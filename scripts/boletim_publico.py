"""Boletim para divulgação à população (somente dados agregados, sem dados pessoais).

Uso:
    python3 scripts/boletim_publico.py ENTRADA [ENTRADA ...] [opções]

Opções:
    --data-ref AAAA-MM-DD  data de referência (padrão: hoje)
    --semanas N            semanas mostradas no gráfico (padrão: 12)
    --minimo N             bairros com menos casos que isso são somados em "Outras localidades" (padrão: 5)
    --municipio TEXTO      nome no título (padrão: Uniflor-PR)
    --contato TEXTO        telefone ou endereço da unidade de saúde, impresso no rodapé
    --saida PASTA          pasta de saída (padrão: saida/publico)

Gera:
    boletim_AAAA-MM-DD.png   imagem 1080x1350 para WhatsApp, Instagram e mural
    boletim_AAAA-MM-DD.html  página com a imagem e os números em texto
"""
import argparse
import base64
import html
from datetime import date, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from comum import RAIZ, bairros_cnefe, inicio_semana, ler_fichas, padronizar_bairro, semana_epi

VERDE, LARANJA, CINZA, TINTA = "#0b6e4f", "#d0621f", "#5b6670", "#1d2329"
PREVENCAO = [
    "Elimine água parada: vire garrafas e baldes, tampe caixas d'água,",
    "limpe calhas e coloque areia nos pratinhos de vasos.",
    "Com febre, dor no corpo, dor atrás dos olhos ou manchas na pele,",
    "procure a unidade de saúde. Não tome remédio por conta própria.",
    "Dor forte na barriga, vômitos que não param ou sangramento:",
    "procure atendimento imediatamente.",
]


def agregar(df, ref, semanas, minimo):
    df = df[df["dt_sin_pri"].map(lambda d: pd.isna(d) or d <= ref)]
    prov = df[df["provavel"]]
    numeros = {
        "Casos notificados": len(df),
        "Casos confirmados": int(df["confirmado"].sum()),
        "Em investigação": int((df["classificacao"] == "Em investigação").sum()),
        "Óbitos": int(df["obito_agravo"].sum()),
    }
    ano, se = semana_epi(ref)
    lista = []
    for _ in range(semanas):
        lista.append((ano, se))
        ano, se = semana_epi(inicio_semana(ano, se) - timedelta(days=1))
    lista.reverse()
    cont = prov.groupby(["ano_epi", "se"]).size()
    curva = [(s, int(cont.get((a, s), 0))) for a, s in lista]

    por_bairro = prov["bairro"].value_counts()
    grandes = por_bairro[por_bairro >= minimo]
    outros = int(por_bairro[por_bairro < minimo].sum())
    linhas = list(grandes.items()) + ([("Outras localidades", outros)] if outros else [])
    return numeros, curva, linhas, len(prov)


def imagem(numeros, curva, bairros, municipio, ref, contato, destino):
    ano, se = semana_epi(ref)
    fig = plt.figure(figsize=(10.8, 13.5), dpi=100)
    fig.patch.set_facecolor("white")
    fig.add_artist(plt.Rectangle((0, .875), 1, .125, color=VERDE, transform=fig.transFigure))
    fig.text(.05, .945, f"Boletim Dengue e Chikungunya", color="white", fontsize=30, weight="bold", va="center")
    fig.text(.05, .9, f"{municipio}  ·  Semana epidemiológica {se}/{ano}  ·  atualizado em {ref:%d/%m/%Y}",
             color="white", fontsize=15, va="center")

    for i, (rot, val) in enumerate(numeros.items()):
        x = .05 + i * .235
        fig.add_artist(plt.Rectangle((x, .76), .2, .095, color="#f1f4f6", transform=fig.transFigure))
        fig.text(x + .1, .82, f"{val}", ha="center", va="center", fontsize=40, weight="bold",
                 color=LARANJA if rot == "Óbitos" and val else TINTA)
        fig.text(x + .1, .773, rot, ha="center", va="center", fontsize=13, color=CINZA)

    ax = fig.add_axes([.08, .475, .86, .22])
    ax.bar([str(s) for s, _ in curva], [n for _, n in curva], color=LARANJA, width=.75)
    for s, n in curva:
        if n:
            ax.text(str(s), n, str(n), ha="center", va="bottom", fontsize=11, color=TINTA)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.set_yticks([])
    ax.tick_params(axis="x", labelsize=11, colors=CINZA)
    fig.text(.05, .725, "Casos prováveis por semana de início dos sintomas", fontsize=18, weight="bold", color=TINTA)
    fig.text(.05, .44, "Semana epidemiológica. As últimas semanas ainda podem aumentar com novas notificações.", fontsize=11, color=CINZA)

    fig.text(.05, .39, "Casos prováveis por bairro", fontsize=18, weight="bold", color=TINTA)
    y = .355
    maior = max([n for _, n in bairros] + [1])
    for nome, n in bairros[:8]:
        fig.text(.05, y, nome, fontsize=13, color=TINTA, va="center")
        fig.add_artist(plt.Rectangle((.45, y - .008), .4 * n / maior, .016, color=LARANJA, transform=fig.transFigure))
        fig.text(.45 + .4 * n / maior + .01, y, str(n), fontsize=13, color=TINTA, va="center")
        y -= .028
    if not bairros:
        fig.text(.05, y, "Nenhum caso provável no período.", fontsize=13, color=CINZA)

    fig.add_artist(plt.Rectangle((.04, .045), .92, .14, color="#e3f2ec", transform=fig.transFigure))
    fig.text(.06, .17, "Como se proteger", fontsize=16, weight="bold", color=VERDE, va="center")
    for i, linha in enumerate(PREVENCAO):
        fig.text(.06, .145 - i * .0165, linha, fontsize=12.5, color=TINTA, va="center",
                 weight="bold" if i >= 4 else "normal")
    rodape = "Fonte: Vigilância Epidemiológica. Dados preliminares, sujeitos a revisão."
    if contato:
        rodape += f"  ·  {contato}"
    fig.text(.05, .02, rodape, fontsize=10.5, color=CINZA)
    fig.savefig(destino, dpi=100, facecolor="white")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entradas", nargs="+")
    ap.add_argument("--data-ref", type=date.fromisoformat, default=date.today())
    ap.add_argument("--semanas", type=int, default=12)
    ap.add_argument("--minimo", type=int, default=5)
    ap.add_argument("--municipio", default="Uniflor-PR")
    ap.add_argument("--contato", default="")
    ap.add_argument("--saida", type=Path, default=RAIZ / "saida" / "publico")
    a = ap.parse_args()

    df, _ = ler_fichas(a.entradas)
    df["bairro"] = padronizar_bairro(df, bairros_cnefe())
    numeros, curva, bairros, n_prov = agregar(df, a.data_ref, a.semanas, a.minimo)
    a.saida.mkdir(parents=True, exist_ok=True)
    png = a.saida / f"boletim_{a.data_ref.isoformat()}.png"
    imagem(numeros, curva, bairros, a.municipio, a.data_ref, a.contato, png)

    ano, se = semana_epi(a.data_ref)
    linhas_num = "".join(f"<tr><td>{html.escape(k)}</td><td>{v}</td></tr>" for k, v in numeros.items())
    linhas_se = "".join(f"<tr><td>{s}</td><td>{n}</td></tr>" for s, n in curva)
    linhas_b = "".join(f"<tr><td>{html.escape(b)}</td><td>{n}</td></tr>" for b, n in bairros)
    dica = "".join(f"<li>{html.escape(t)}</li>" for t in [
        "Elimine água parada: vire garrafas e baldes, tampe caixas d'água, limpe calhas e coloque areia nos pratinhos de vasos.",
        "Com febre, dor no corpo, dor atrás dos olhos ou manchas na pele, procure a unidade de saúde. Não tome remédio por conta própria.",
        "Dor forte na barriga, vômitos que não param ou sangramento: procure atendimento imediatamente."])
    (a.saida / f"boletim_{a.data_ref.isoformat()}.html").write_text(f"""<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Boletim Dengue – {html.escape(a.municipio)}</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:760px;margin:0 auto;padding:16px;color:#1d2329}}
img{{width:100%;height:auto;border-radius:8px}}h1{{font-size:22px;color:#0b6e4f}}h2{{font-size:18px}}
table{{border-collapse:collapse}}td{{border-bottom:1px solid #d5dbe0;padding:4px 12px 4px 0}}.n{{color:#5b6670;font-size:14px}}</style>
</head><body>
<h1>Boletim Dengue e Chikungunya – {html.escape(a.municipio)}</h1>
<p>Semana epidemiológica {se}/{ano}, atualizado em {a.data_ref:%d/%m/%Y}.</p>
<img alt="Boletim com os números de dengue e chikungunya da semana" src="data:image/png;base64,{base64.b64encode(png.read_bytes()).decode()}">
<h2>Números</h2><table>{linhas_num}</table>
<h2>Casos prováveis por semana de início dos sintomas</h2><table><tr><td><b>Semana</b></td><td><b>Casos</b></td></tr>{linhas_se}</table>
<p class="n">As últimas semanas ainda podem aumentar com novas notificações.</p>
<h2>Casos prováveis por bairro</h2><table>{linhas_b}</table>
<p class="n">Bairros e localidades com menos de {a.minimo} casos foram somados em "Outras localidades" para proteger a privacidade.</p>
<h2>Como se proteger</h2><ul>{dica}</ul>
<p class="n">Fonte: Vigilância Epidemiológica. Dados preliminares, sujeitos a revisão. {html.escape(a.contato)}</p>
</body></html>""", encoding="utf-8")
    print(f"{numeros['Casos notificados']} notificados, {n_prov} prováveis. Boletim: {png}")


if __name__ == "__main__":
    main()
