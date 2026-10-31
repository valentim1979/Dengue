"""Funções comuns: leitura das tabelas exportadas pelo formulário e variáveis derivadas."""
import csv
import math
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CNEFE_PADRAO = RAIZ / "dados" / "cnefe_2022_4128302_uniflor.csv"

AGRAVO = {"1": "Dengue", "2": "Chikungunya"}
CLASSIFICACAO = {"5": "Descartado", "10": "Dengue", "11": "Dengue com sinais de alarme",
                 "12": "Dengue grave", "13": "Chikungunya"}
SEXO = {"M": "Masculino", "F": "Feminino", "I": "Ignorado"}
EVOLUCAO = {"1": "Cura", "2": "Óbito pelo agravo", "3": "Óbito por outras causas",
            "4": "Óbito em investigação", "9": "Ignorado"}
GEO_METODO = {"1": "Número exato", "2": "Interpolado", "3": "Número mais próximo",
              "4": "Centro da rua", "5": "Centro do bairro"}
SINAIS = {"febre": "Febre", "mialgia": "Mialgia", "cefaleia": "Cefaleia", "exantema": "Exantema",
          "vomito": "Vômito", "nausea": "Náuseas", "dor_costas": "Dor nas costas",
          "conjuntvit": "Conjuntivite", "artrite": "Artrite", "artralgia": "Artralgia intensa",
          "petequia_n": "Petéquias", "leucopenia": "Leucopenia", "laco": "Prova do laço positiva",
          "dor_retro": "Dor retroorbital"}
FAIXAS = [(0, 4, "0 a 4"), (5, 9, "5 a 9"), (10, 19, "10 a 19"), (20, 39, "20 a 39"),
          (40, 59, "40 a 59"), (60, 79, "60 a 79"), (80, 200, "80 ou mais")]


def norm(texto):
    texto = unicodedata.normalize("NFD", str(texto or "")).encode("ascii", "ignore").decode()
    return " ".join(texto.lower().split())


def semana_epi(d):
    """Semana epidemiológica (domingo a sábado). A SE 1 é a que contém 4 de janeiro."""
    def inicio(ano):
        j4 = date(ano, 1, 4)
        return j4 - timedelta(days=(j4.weekday() + 1) % 7)
    ano = d.year + 1
    while d < inicio(ano):
        ano -= 1
    return ano, (d - inicio(ano)).days // 7 + 1


def inicio_semana(ano, se):
    j4 = date(ano, 1, 4)
    return j4 - timedelta(days=(j4.weekday() + 1) % 7) + timedelta(weeks=se - 1)


def idade_anos(idade, unidade):
    try:
        v = float(idade)
    except (TypeError, ValueError):
        return math.nan
    return {"1": v / 8760, "2": v / 365, "3": v / 12, "4": v}.get(str(unidade), math.nan)


def faixa(anos):
    if pd.isna(anos) or anos < 0:
        return "Ignorada"
    anos = int(anos)
    for a, b, nome in FAIXAS:
        if a <= anos <= b:
            return nome
    return "Ignorada"


def distancia_m(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def ler_fichas(caminhos):
    """Lê um ou mais CSV exportados (arquivos ou pastas) e remove registros repetidos.

    Quando a mesma ficha aparece em mais de um arquivo, fica a versão gravada por último.
    """
    arquivos = []
    for c in map(Path, caminhos):
        arquivos += sorted(c.glob("*.csv")) if c.is_dir() else [c]
    if not arquivos:
        raise SystemExit("Nenhum arquivo CSV encontrado.")
    partes = [pd.read_csv(a, sep=";", dtype=str, encoding="utf-8-sig", keep_default_na=False) for a in arquivos]
    df = pd.concat(partes, ignore_index=True)
    if "id_registro" not in df.columns:
        raise SystemExit("Os arquivos não parecem ser tabelas exportadas pelo formulário (falta id_registro).")
    df = df.sort_values("salvo_em").drop_duplicates("id_registro", keep="last").reset_index(drop=True)
    return preparar(df), arquivos


COLUNAS_USADAS = ["dt_notific", "dt_sin_pri", "dt_nasc", "idade", "idade_un", "agravo", "classi_fin",
                  "cs_sexo", "cs_gestant", "evolucao", "hospitaliz", "nm_pacient", "nm_bairro", "nm_logrado",
                  "nu_numero", "latitude", "longitude", "geo_metodo", "geo_setor", "salvo_em", *SINAIS]


def preparar(df):
    df = df.copy()
    for c in COLUNAS_USADAS:
        if c not in df.columns:
            df[c] = ""
    for c in [c for c in df.columns if c.startswith("dt_")]:
        df[c] = pd.to_datetime(df[c], errors="coerce").dt.date
    for c in ("latitude", "longitude"):
        df[c] = pd.to_numeric(df.get(c, ""), errors="coerce")
    df["classificacao"] = df["classi_fin"].map(CLASSIFICACAO).fillna("Em investigação")
    df["agravo_nome"] = df["agravo"].map(AGRAVO).fillna("Ignorado")
    df["sexo"] = df["cs_sexo"].map(SEXO).fillna("Ignorado")
    df["provavel"] = df["classi_fin"] != "5"
    df["confirmado"] = df["classi_fin"].isin(["10", "11", "12", "13"])
    df["obito_agravo"] = df["evolucao"] == "2"
    df["hospitalizado"] = df["hospitaliz"] == "1"
    ref = df["dt_sin_pri"].where(df["dt_sin_pri"].notna(), df["dt_notific"])
    se = ref.map(lambda d: semana_epi(d) if isinstance(d, date) else (None, None))
    df["ano_epi"] = se.map(lambda x: x[0])
    df["se"] = se.map(lambda x: x[1])
    nasc = pd.to_datetime(df["dt_nasc"], errors="coerce")
    refdt = pd.to_datetime(ref, errors="coerce")
    anos_nasc = (refdt - nasc).dt.days / 365.25
    df["idade_anos"] = anos_nasc.where(anos_nasc.notna(), [idade_anos(i, u) for i, u in zip(df["idade"], df["idade_un"])])
    df["faixa_etaria"] = df["idade_anos"].map(faixa)
    df["dias_sint_notif"] = (pd.to_datetime(df["dt_notific"]) - pd.to_datetime(df["dt_sin_pri"])).dt.days
    return df


def bairros_cnefe(caminho=CNEFE_PADRAO):
    """Domicílios e centro aproximado de cada bairro/localidade a partir do CNEFE."""
    dados = {}
    with open(caminho, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            nome = " ".join(w if w in ("da", "das", "de", "do", "dos") else w.capitalize()
                            for w in r["DSC_LOCALIDADE"].lower().split())
            d = dados.setdefault(norm(nome), {"bairro": nome, "domicilios": 0, "lat": [], "lon": []})
            if r["COD_ESPECIE"] in ("1", "2"):
                d["domicilios"] += 1
            d["lat"].append(float(r["LATITUDE"]))
            d["lon"].append(float(r["LONGITUDE"]))
    linhas = [{"chave": k, "bairro": v["bairro"], "domicilios": v["domicilios"],
               "lat": sum(v["lat"]) / len(v["lat"]), "lon": sum(v["lon"]) / len(v["lon"])}
              for k, v in dados.items()]
    return pd.DataFrame(linhas)


def padronizar_bairro(df, bairros):
    """Usa o nome do CNEFE quando o bairro digitado coincide (ignorando acentos e maiúsculas)."""
    nomes = dict(zip(bairros["chave"], bairros["bairro"]))
    return df["nm_bairro"].map(lambda b: nomes.get(norm(b), b.strip().title() if b and b.strip() else "Não informado"))
