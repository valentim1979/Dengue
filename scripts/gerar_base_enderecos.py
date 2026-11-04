"""Gera as bases de endereços (uma por município) a partir do CNEFE 2022 (IBGE).

Uso:
    python3 scripts/gerar_base_enderecos.py CSV_OU_PASTA [CSV ...] [--saida bases]

Cada CSV do IBGE (ex.: 4128302_UNIFLOR.csv) vira bases/4128302.json, usado pelo
formulário (sugestões de bairro e rua, cálculo de coordenadas) e pelos relatórios.
Também atualiza bases/municipios.json com a lista de municípios disponíveis.

Os CSV por município estão em:
https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/Censo_Demografico_2022/Arquivos_CNEFE/CSV/Municipio/
"""
import argparse
import csv
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MINUSCULAS = {"da", "das", "de", "do", "dos", "e"}


def titulo(texto):
    palavras = texto.strip().lower().split()
    return " ".join(p if i and p in MINUSCULAS else p.capitalize() for i, p in enumerate(palavras))


def gerar(caminho, nome=None):
    """Lê um CSV do CNEFE e devolve a base compacta do município.

    pontos: [índice da rua, número, latitude×1e6, longitude×1e6, índice do setor]
    bairros: [nome, domicílios, latitude, longitude] (centro médio dos endereços)
    """
    pares, setores, pontos, vistos = [], [], [], set()
    idx_par, idx_setor, bairros = {}, {}, {}
    codigo = None
    with open(caminho, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            codigo = codigo or r["COD_MUNICIPIO"]
            if not r["LATITUDE"] or not r["LONGITUDE"]:
                continue
            lat, lon = float(r["LATITUDE"]), float(r["LONGITUDE"])
            bairro = titulo(r["DSC_LOCALIDADE"])
            b = bairros.setdefault(bairro, [0, 0.0, 0.0, 0])
            b[0] += r["COD_ESPECIE"] in ("1", "2")
            b[1] += lat
            b[2] += lon
            b[3] += 1
            rua = titulo(" ".join(x for x in (r["NOM_TIPO_SEGLOGR"], r["NOM_TITULO_SEGLOGR"], r["NOM_SEGLOGR"]) if x))
            if not rua:
                continue
            par = (bairro, rua)
            if par not in idx_par:
                idx_par[par] = len(pares)
                pares.append(list(par))
            if r["COD_SETOR"] not in idx_setor:
                idx_setor[r["COD_SETOR"]] = len(setores)
                setores.append(r["COD_SETOR"])
            num = int(r["NUM_ENDERECO"]) if r["NUM_ENDERECO"].isdigit() else 0
            p = (idx_par[par], num, round(lat * 1e6), round(lon * 1e6), idx_setor[r["COD_SETOR"]])
            if p not in vistos:
                vistos.add(p)
                pontos.append(list(p))

    ordem = sorted(range(len(pares)), key=lambda i: (pares[i][1], pares[i][0]))
    novo = {antigo: n for n, antigo in enumerate(ordem)}
    pares = [pares[i] for i in ordem]
    for p in pontos:
        p[0] = novo[p[0]]
    pontos.sort()
    return {
        "codigo": codigo,
        "nome": nome or titulo(Path(caminho).stem.split("_", 1)[-1].replace("_", " ")),
        "fonte": "IBGE, CNEFE Censo 2022",
        "ruas": pares,
        "setores": setores,
        "pontos": pontos,
        "bairros": sorted([[k, v[0], round(v[1] / v[3], 6), round(v[2] / v[3], 6)] for k, v in bairros.items()]),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entradas", nargs="+", type=Path)
    ap.add_argument("--nomes", type=Path, help="CSV codigo;nome com os nomes acentuados dos municípios")
    ap.add_argument("--saida", type=Path, default=RAIZ / "bases")
    a = ap.parse_args()

    nomes = {}
    if a.nomes:
        with open(a.nomes, encoding="utf-8") as f:
            nomes = {r["codigo"]: r["nome"] for r in csv.DictReader(f, delimiter=";")}
    arquivos = [x for e in a.entradas for x in (sorted(e.glob("*.csv")) if e.is_dir() else [e])]
    a.saida.mkdir(parents=True, exist_ok=True)

    indice_path = a.saida / "municipios.json"
    indice = {m["codigo"]: m for m in json.loads(indice_path.read_text(encoding="utf-8"))} if indice_path.exists() else {}
    for arq in arquivos:
        cod = arq.name.split("_", 1)[0]
        base = gerar(arq, nomes.get(cod))
        destino = a.saida / f"{base['codigo']}.json"
        destino.write_text(json.dumps(base, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        indice[base["codigo"]] = {"codigo": base["codigo"], "nome": base["nome"], "uf": "PR" if base["codigo"].startswith("41") else ""}
        print(f"{base['nome']}: {len(base['ruas'])} ruas, {len(base['pontos'])} pontos, "
              f"{destino.stat().st_size / 1e6:.1f} MB")
    lista = sorted(indice.values(), key=lambda m: m["nome"])
    indice_path.write_text(json.dumps(lista, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{len(lista)} municípios em {indice_path}")


if __name__ == "__main__":
    main()
