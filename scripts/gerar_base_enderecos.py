"""Gera a base de endereços embutida no index.html a partir do CNEFE 2022 (IBGE).

Uso:
    python3 scripts/gerar_base_enderecos.py dados/cnefe_2022_4128302_uniflor.csv index.html

O arquivo CSV do município está em:
https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/Censo_Demografico_2022/Arquivos_CNEFE/CSV/Municipio/

O script substitui o trecho entre /*CNEFE-INICIO*/ e /*CNEFE-FIM*/ no index.html
e grava dados/lista_ruas.csv (bairro;rua).
"""
import csv
import json
import re
import sys
from pathlib import Path

MINUSCULAS = {"da", "das", "de", "do", "dos", "e"}


def titulo(texto):
    palavras = texto.strip().lower().split()
    return " ".join(p if i and p in MINUSCULAS else p.capitalize() for i, p in enumerate(palavras))


def main(cnefe, html):
    with open(cnefe, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))

    pares, setores, pontos, vistos = [], [], [], set()
    idx_par, idx_setor = {}, {}
    for r in linhas:
        if not r["LATITUDE"] or not r["LONGITUDE"]:
            continue
        rua = titulo(" ".join(x for x in (r["NOM_TIPO_SEGLOGR"], r["NOM_TITULO_SEGLOGR"], r["NOM_SEGLOGR"]) if x))
        par = (titulo(r["DSC_LOCALIDADE"]), rua)
        if par not in idx_par:
            idx_par[par] = len(pares)
            pares.append(list(par))
        if r["COD_SETOR"] not in idx_setor:
            idx_setor[r["COD_SETOR"]] = len(setores)
            setores.append(r["COD_SETOR"])
        num = int(r["NUM_ENDERECO"]) if r["NUM_ENDERECO"].isdigit() else 0
        p = (idx_par[par], num, round(float(r["LATITUDE"]), 6), round(float(r["LONGITUDE"]), 6), idx_setor[r["COD_SETOR"]])
        if p not in vistos:
            vistos.add(p)
            pontos.append(list(p))

    ordem = sorted(range(len(pares)), key=lambda i: (pares[i][1], pares[i][0]))
    novo = {antigo: novo for novo, antigo in enumerate(ordem)}
    pares = [pares[i] for i in ordem]
    for p in pontos:
        p[0] = novo[p[0]]
    pontos.sort()

    base = {"fonte": "IBGE, CNEFE Censo 2022, município " + linhas[0]["COD_MUNICIPIO"],
            "ruas": pares, "setores": setores, "pontos": pontos}
    trecho = "/*CNEFE-INICIO*/const CNEFE = " + json.dumps(base, ensure_ascii=False, separators=(",", ":")) + ";/*CNEFE-FIM*/"

    texto = Path(html).read_text(encoding="utf-8")
    texto, n = re.subn(r"/\*CNEFE-INICIO\*/.*?/\*CNEFE-FIM\*/", lambda m: trecho, texto, flags=re.S)
    if n != 1:
        sys.exit("Marcadores /*CNEFE-INICIO*/ e /*CNEFE-FIM*/ não encontrados no HTML")
    Path(html).write_text(texto, encoding="utf-8")

    saida = Path(html).parent / "dados" / "lista_ruas.csv"
    with open(saida, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["bairro", "rua"])
        w.writerows(pares)

    print(f"{len(linhas)} linhas lidas, {len(pares)} pares bairro/rua, {len(pontos)} pontos, {len(setores)} setores")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
