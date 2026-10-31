"""Relatório interno da vigilância epidemiológica (contém dados pessoais).

Uso:
    python3 scripts/relatorio_epidemiologico.py ENTRADA [ENTRADA ...] [opções]

ENTRADA é um CSV exportado pelo formulário ou uma pasta com vários (um por tablet).
Fichas repetidas entre arquivos são contadas uma vez.

Opções:
    --data-ref AAAA-MM-DD  data de referência (padrão: hoje)
    --dias N               janela para lista de bloqueio e áreas de atenção (padrão: 14)
    --raio M               raio em metros de cada área de atenção (padrão: 200)
    --minimo N             casos para formar área de atenção (padrão: 3)
    --populacao N          população do município, para calcular incidência por 100 mil hab.
    --saida PASTA          pasta de saída (padrão: saida/interno)

Gera na pasta de saída:
    relatorio_AAAA-MM-DD.html   relatório com gráficos e tabelas
    mapa_casos.html             mapa dos casos (precisa de internet para o mapa de fundo)
    lista_bloqueio.csv          casos prováveis recentes com endereço, para a equipe de endemias
    areas_atencao.csv           grupos de casos próximos no espaço e no tempo
    casos_por_se.csv, casos_por_bairro.csv
"""
import argparse
import base64
import html
import io
import json
from datetime import date, timedelta
from pathlib import Path

import matplotlib
import matplotlib.patches
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from comum import (CLASSIFICACAO, CNEFE_PADRAO, FAIXAS, GEO_METODO, RAIZ, SINAIS, bairros_cnefe, distancia_m,
                   inicio_semana, ler_fichas, padronizar_bairro, semana_epi)

CORES = {"Em investigação": "#9aa5ae", "Descartado": "#d5dbe0", "Dengue": "#e8a33d",
         "Dengue com sinais de alarme": "#d0621f", "Dengue grave": "#a3201c", "Chikungunya": "#6a4fb3"}
ORDEM = ["Dengue", "Dengue com sinais de alarme", "Dengue grave", "Chikungunya", "Em investigação", "Descartado"]


def png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return '<img alt="" src="data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode() + '">'


def tabela(df, indice=False):
    return df.to_html(index=indice, border=0, classes="t", na_rep="", escape=True)


def curva(df):
    d = df.dropna(subset=["se"])
    if d.empty:
        return None, "<p>Sem datas de início de sintomas.</p>"
    d = d.assign(chave=list(zip(d["ano_epi"].astype(int), d["se"].astype(int))))
    ini, fim = min(d["chave"]), max(d["chave"])
    semanas, a, s = [], *ini
    while (a, s) <= fim:
        semanas.append((a, s))
        prox = inicio_semana(a, s) + timedelta(weeks=1)
        a, s = semana_epi(prox)
    tab = d.groupby(["chave", "classificacao"]).size().unstack(fill_value=0).reindex(semanas, fill_value=0)
    tab = tab[[c for c in ORDEM if c in tab.columns]]
    fig, ax = plt.subplots(figsize=(10, 4))
    base = [0] * len(tab)
    rot = [f"{s}" for _, s in tab.index]
    for c in tab.columns:
        ax.bar(rot, tab[c], bottom=base, color=CORES[c], label=c, width=.85)
        base = [x + y for x, y in zip(base, tab[c])]
    ax.set_xlabel("Semana epidemiológica de início dos sintomas")
    ax.set_ylabel("Casos notificados")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8, ncol=3)
    if len(rot) > 20:
        for i, t in enumerate(ax.get_xticklabels()):
            t.set_visible(i % 2 == 0)
    saida = tab.copy()
    saida.index = [f"{a}-SE{s:02d}" for a, s in tab.index]
    saida.index.name = "semana"
    saida["total"] = saida.sum(axis=1)
    return saida, png(fig)


def por_bairro(df, bairros, populacao):
    p = df[df["provavel"]]
    t = p.groupby("bairro").agg(casos_provaveis=("id_registro", "size"),
                                confirmados=("confirmado", "sum"),
                                hospitalizados=("hospitalizado", "sum")).reset_index()
    t = t.merge(bairros[["bairro", "domicilios"]], on="bairro", how="left")
    t["casos_por_1000_domicilios"] = (t["casos_provaveis"] / t["domicilios"] * 1000).round(1)
    t = t.sort_values("casos_provaveis", ascending=False)
    fig, ax = plt.subplots(figsize=(7, max(2, .4 * len(t))))
    ax.barh(t["bairro"][::-1], t["casos_provaveis"][::-1], color="#d0621f")
    ax.set_xlabel("Casos prováveis")
    ax.spines[["top", "right"]].set_visible(False)
    return t, png(fig)


def piramide(df):
    p = df[df["provavel"]]
    ordem = [f[2] for f in FAIXAS] + ["Ignorada"]
    t = p.groupby(["faixa_etaria", "sexo"]).size().unstack(fill_value=0).reindex(ordem, fill_value=0)
    for s in ("Masculino", "Feminino"):
        if s not in t.columns:
            t[s] = 0
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.barh(t.index, -t["Masculino"], color="#4a7fb5", label="Masculino")
    ax.barh(t.index, t["Feminino"], color="#c45a8a", label="Feminino")
    m = max(t["Masculino"].max(), t["Feminino"].max(), 1)
    ax.set_xlim(-m * 1.15, m * 1.15)
    ax.set_xticks(ax.get_xticks())
    ax.set_xticklabels([str(abs(int(x))) for x in ax.get_xticks()])
    ax.axvline(0, color="#888", lw=.6)
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlabel("Casos prováveis")
    return png(fig)


def areas_atencao(rec, raio, minimo):
    """Áreas compactas de casos recentes: o caso com mais vizinhos a até `raio` metros vira o centro
    de uma área, os casos dessa área saem da conta e o processo se repete."""
    pts = rec.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)
    coords = list(zip(pts["latitude"], pts["longitude"]))
    viz = [{j for j, q in enumerate(coords) if distancia_m(*p, *q) <= raio} for p in coords]
    livres, linhas = set(range(len(pts))), []
    while livres:
        centro = max(livres, key=lambda i: (len(viz[i] & livres), -i))
        membros = viz[centro] & livres
        if len(membros) < minimo:
            break
        livres -= membros
        g = pts.loc[sorted(membros)]
        linhas.append({"casos": len(g), "bairros": ", ".join(sorted(set(g["bairro"]))),
                       "ruas": ", ".join(sorted(set(g["nm_logrado"]))),
                       "primeiro_inicio_sintomas": min(g["dt_sin_pri"]), "ultimo_inicio_sintomas": max(g["dt_sin_pri"]),
                       "latitude_centro": round(pts.at[centro, "latitude"], 6), "longitude_centro": round(pts.at[centro, "longitude"], 6)})
    t = pd.DataFrame(linhas, columns=["casos", "bairros", "ruas", "primeiro_inicio_sintomas", "ultimo_inicio_sintomas",
                                      "latitude_centro", "longitude_centro"])
    return t.sort_values("casos", ascending=False).reset_index(drop=True)


def mapa_estatico(df, areas, raio):
    """Mapa sem internet: endereços do CNEFE em cinza ao fundo, casos coloridos por classificação.
    À esquerda o município; à direita a área urbana (localidade com mais endereços) ampliada."""
    import csv
    import math
    from collections import Counter
    with open(CNEFE_PADRAO, encoding="utf-8") as f:
        fundo = [(float(r["LONGITUDE"]), float(r["LATITUDE"]), r["DSC_LOCALIDADE"]) for r in csv.DictReader(f, delimiter=";")]
    pts = df.dropna(subset=["latitude", "longitude"])
    if pts.empty:
        return "<p>Nenhum caso com coordenada.</p>"
    urbana = Counter(x[2] for x in fundo).most_common(1)[0][0]
    caixas = [(min(x[0] for x in fundo), max(x[0] for x in fundo), min(x[1] for x in fundo), max(x[1] for x in fundo)),
              tuple(f(x[i] for x in fundo if x[2] == urbana) for i in (0, 1) for f in (min, max))]
    fig, eixos = plt.subplots(1, 2, figsize=(13, 6.5), gridspec_kw={"width_ratios": [1, 1]})
    for ax, (lon0, lon1, lat0, lat1), titulo in zip(eixos, caixas, ["Município", f"Área urbana ({urbana.title()})"]):
        mx, my = (lon1 - lon0) * .05 + .0005, (lat1 - lat0) * .05 + .0005
        ax.scatter([x[0] for x in fundo], [x[1] for x in fundo], s=3, color="#c9cfd4", zorder=1, label="Endereços (IBGE)")
        for c in reversed(ORDEM):
            g = pts[pts["classificacao"] == c]
            if len(g):
                ax.scatter(g["longitude"], g["latitude"], s=24, color=CORES[c], edgecolor="#222", linewidth=.4, zorder=3, label=c)
        for r in areas.itertuples():
            dlat = raio / 111320
            ax.add_patch(matplotlib.patches.Ellipse((r.longitude_centro, r.latitude_centro),
                                                    2 * dlat / math.cos(math.radians(r.latitude_centro)), 2 * dlat,
                                                    fill=False, ls="--", lw=1.2, color="#a3201c", zorder=4))
        ax.set_xlim(lon0 - mx, lon1 + mx)
        ax.set_ylim(lat0 - my, lat1 + my)
        ax.set_aspect(1 / math.cos(math.radians((lat0 + lat1) / 2)))
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(titulo, fontsize=11)
    h, l = eixos[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=len(l), frameon=False, fontsize=9)
    fig.subplots_adjust(bottom=.08)
    return png(fig)


def mapa(df, areas, raio, destino):
    pts = df.dropna(subset=["latitude", "longitude"])
    dados = [{"lat": r.latitude, "lon": r.longitude, "cor": CORES.get(r.classificacao, "#888"),
              "txt": f"{html.escape(r.nm_pacient)}<br>{html.escape(r.nm_logrado)}, {html.escape(r.nu_numero)} – {html.escape(r.bairro)}"
                     f"<br>Início: {r.dt_sin_pri}<br>{r.classificacao}"} for r in pts.itertuples()]
    ar = [{"lat": r.latitude_centro, "lon": r.longitude_centro, "n": int(r.casos)} for r in areas.itertuples()]
    legenda = "".join(f'<span><i style="background:{c}"></i>{k}</span>' for k, c in CORES.items())
    destino.write_text(f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Mapa de casos – uso interno</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>html,body{{margin:0;height:100%;font:14px system-ui,sans-serif}}#m{{height:calc(100% - 64px)}}
.top{{padding:8px 12px;background:#a3201c;color:#fff}}.leg{{padding:4px 12px;display:flex;flex-wrap:wrap;gap:10px;font-size:12px}}
.leg i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px}}</style></head><body>
<div class="top">USO INTERNO – contém dados pessoais de saúde. Não divulgar. Círculos tracejados: áreas de atenção (raio de {raio:.0f} m).</div>
<div class="leg">{legenda}</div><div id="m"></div>
<script>
const P={json.dumps(dados, ensure_ascii=False)}, A={json.dumps(ar)};
const m=L.map('m');L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:19,attribution:'© OpenStreetMap'}}).addTo(m);
const g=L.featureGroup().addTo(m);
P.forEach(p=>L.circleMarker([p.lat,p.lon],{{radius:6,color:'#222',weight:1,fillColor:p.cor,fillOpacity:.9}}).bindPopup(p.txt).addTo(g));
A.forEach(a=>L.circle([a.lat,a.lon],{{radius:{raio},color:'#a3201c',dashArray:'6',fill:false}}).bindPopup(a.n+' casos').addTo(g));
if(P.length) m.fitBounds(g.getBounds().pad(.1)); else m.setView([-23.085,-52.159],14);
</script></body></html>""", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entradas", nargs="+")
    ap.add_argument("--data-ref", type=date.fromisoformat, default=date.today())
    ap.add_argument("--dias", type=int, default=14)
    ap.add_argument("--raio", type=float, default=200)
    ap.add_argument("--minimo", type=int, default=3)
    ap.add_argument("--populacao", type=int)
    ap.add_argument("--saida", type=Path, default=RAIZ / "saida" / "interno")
    a = ap.parse_args()

    df, arquivos = ler_fichas(a.entradas)
    bairros = bairros_cnefe()
    df["bairro"] = padronizar_bairro(df, bairros)
    a.saida.mkdir(parents=True, exist_ok=True)
    ref, (ano_ref, se_ref) = a.data_ref, semana_epi(a.data_ref)

    prov = df[df["provavel"]]
    resumo = [
        ("Fichas notificadas", len(df)),
        ("Casos prováveis (exceto descartados)", len(prov)),
        ("Em investigação (sem classificação)", int((df["classificacao"] == "Em investigação").sum())),
        ("Descartados", int((df["classi_fin"] == "5").sum())),
        *[(f"Confirmados – {CLASSIFICACAO[k]}", int((df["classi_fin"] == k).sum())) for k in ("10", "11", "12", "13")],
        ("Hospitalizados", int(df["hospitalizado"].sum())),
        ("Óbitos pelo agravo", int(df["obito_agravo"].sum())),
        ("Gestantes entre os casos prováveis", int(prov["cs_gestant"].isin(["1", "2", "3", "4"]).sum())),
    ]
    if a.populacao:
        resumo.append(("Incidência de casos prováveis por 100 mil hab.", round(len(prov) / a.populacao * 1e5, 1)))
    resumo = pd.DataFrame([(k, f"{v:g}".replace(".", ",")) for k, v in resumo], columns=["Indicador", "Valor"])

    tab_se, img_curva = curva(df)
    tab_bairro, img_bairro = por_bairro(df, bairros, a.populacao)
    img_pir = piramide(df)

    sinais = pd.DataFrame([(nome, int((prov[c] == "1").sum()), round((prov[c] == "1").mean() * 100, 1) if len(prov) else 0)
                           for c, nome in SINAIS.items()], columns=["Sinal", "Casos", "%"]).sort_values("Casos", ascending=False)

    dias = df["dias_sint_notif"].dropna()
    oportunidade = pd.DataFrame([
        ("Mediana de dias entre início dos sintomas e notificação", dias.median() if len(dias) else ""),
        ("Notificados em até 7 dias do início dos sintomas (%)", round((dias <= 7).mean() * 100, 1) if len(dias) else ""),
        ("Fichas sem data de início dos sintomas", int(df["dt_sin_pri"].isna().sum())),
    ], columns=["Indicador", "Valor"])

    geo = df["geo_metodo"].map(GEO_METODO).fillna("Sem coordenada").value_counts().rename_axis("Método").reset_index(name="Fichas")
    sem_coord = df[df["latitude"].isna()][["nm_pacient", "nm_bairro", "nm_logrado", "nu_numero", "dt_notific"]]

    janela = ref - timedelta(days=a.dias)
    rec = prov[prov["dt_sin_pri"].map(lambda d: d is not None and not pd.isna(d) and janela <= d <= ref)]
    bloqueio = rec[["nm_pacient", "bairro", "nm_logrado", "nu_numero", "dt_sin_pri", "classificacao",
                    "latitude", "longitude", "geo_setor"]].sort_values(["bairro", "nm_logrado", "nu_numero"])
    areas = areas_atencao(rec, a.raio, a.minimo)

    tab_se.to_csv(a.saida / "casos_por_se.csv", sep=";", encoding="utf-8-sig")
    tab_bairro.to_csv(a.saida / "casos_por_bairro.csv", sep=";", index=False, encoding="utf-8-sig")
    bloqueio.to_csv(a.saida / "lista_bloqueio.csv", sep=";", index=False, encoding="utf-8-sig")
    areas.to_csv(a.saida / "areas_atencao.csv", sep=";", index=False, encoding="utf-8-sig")
    mapa(df, areas, a.raio, a.saida / "mapa_casos.html")

    corpo = f"""
<h1>Dengue e Chikungunya – Uniflor-PR</h1>
<p class="aviso">USO INTERNO. Este relatório contém dados pessoais de saúde. Não divulgar.</p>
<p>Data de referência: {ref:%d/%m/%Y} (SE {se_ref}/{ano_ref}). Fichas lidas de {len(arquivos)} arquivo(s).</p>
<h2>Resumo</h2>{tabela(resumo)}
<h2>Curva epidêmica</h2>{img_curva}
<h2>Casos prováveis por bairro</h2>
<p class="nota">Denominador: domicílios particulares e coletivos do CNEFE 2022 (IBGE).</p>
{img_bairro}{tabela(tab_bairro)}
<h2>Sexo e faixa etária</h2>{img_pir}
<h2>Sinais clínicos entre os casos prováveis</h2>{tabela(sinais)}
<h2>Oportunidade da notificação</h2>{tabela(oportunidade)}
<h2>Lista de bloqueio – início dos sintomas nos últimos {a.dias} dias</h2>
<p class="nota">{len(bloqueio)} casos prováveis. Arquivo: lista_bloqueio.csv</p>{tabela(bloqueio)}
<h2>Áreas de atenção</h2>
{mapa_estatico(df, areas, a.raio)}
<p class="nota">Mapa com todos os casos. Tracejado: áreas de atenção. Versão interativa: mapa_casos.html (precisa de internet).</p>
<p class="nota">Círculos de {a.raio:.0f} m de raio, centrados num caso, com pelo menos {a.minimo} casos prováveis dos últimos {a.dias} dias.
Veja no arquivo mapa_casos.html.</p>
{tabela(areas) if len(areas) else "<p>Nenhuma área com esses critérios.</p>"}
<h2>Qualidade do georreferenciamento</h2>{tabela(geo)}
{"<h3>Fichas sem coordenada</h3>" + tabela(sem_coord) if len(sem_coord) else ""}
"""
    destino = a.saida / f"relatorio_{ref.isoformat()}.html"
    destino.write_text(f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Relatório Dengue – uso interno</title>
<style>body{{font:15px/1.45 system-ui,sans-serif;max-width:980px;margin:0 auto;padding:16px;color:#1d2329}}
h1{{font-size:22px}}h2{{font-size:17px;margin-top:28px;border-bottom:2px solid #0b6e4f;padding-bottom:4px}}
img{{max-width:100%}}.aviso{{background:#a3201c;color:#fff;padding:8px 12px;border-radius:6px}}
.nota{{color:#5b6670;font-size:13px}}table.t{{border-collapse:collapse;font-size:13px;margin:8px 0;display:block;overflow-x:auto}}
.t th,.t td{{border-bottom:1px solid #d5dbe0;padding:4px 8px;text-align:left}}</style></head><body>{corpo}</body></html>""",
                       encoding="utf-8")
    print(f"{len(df)} fichas, {len(prov)} casos prováveis, {len(bloqueio)} na lista de bloqueio, {len(areas)} áreas de atenção")
    print(f"Relatório: {destino}")


if __name__ == "__main__":
    main()
