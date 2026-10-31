"""Gera fichas FICTÍCIAS no formato exportado pelo formulário, para testar e treinar.

Uso:
    python3 scripts/gerar_dados_teste.py [quantidade] [arquivo_saida]

Os nomes são "Paciente Teste 001", "Paciente Teste 002"... e os endereços são sorteados
da base CNEFE de Uniflor. Nenhum dado é real.
"""
import csv
import random
import sys
import uuid
from datetime import date, timedelta

from comum import CNEFE_PADRAO, RAIZ

COLUNAS = ["id_registro", "salvo_em", "tp_not", "agravo", "dt_notific", "sg_uf_not", "id_municip",
           "cod_mun_not", "id_unidade", "dt_sin_pri", "nm_pacient", "dt_nasc", "idade", "idade_un",
           "cs_sexo", "cs_gestant", "cs_raca", "sg_uf", "id_mn_resi", "nm_bairro", "nm_logrado",
           "end_na_lista", "nu_numero", "latitude", "longitude", "geo_metodo", "geo_setor",
           "febre", "mialgia", "cefaleia", "exantema", "vomito", "nausea", "artralgia", "dor_retro",
           "hospitaliz", "classi_fin", "criterio", "evolucao"]


def titulo(t):
    return " ".join(w if w in ("da", "das", "de", "do", "dos") else w.capitalize() for w in t.lower().split())


def main(n, saida):
    random.seed(42)
    with open(CNEFE_PADRAO, encoding="utf-8") as f:
        enderecos = [r for r in csv.DictReader(f, delimiter=";") if r["COD_ESPECIE"] == "1"]
    hoje = date.today()
    linhas = []
    for i in range(1, n + 1):
        e = random.choice(enderecos)
        # curva epidêmica: mais casos nas últimas semanas
        inicio = hoje - timedelta(days=int(abs(random.gauss(18, 14))) + 1)
        notif = min(inicio + timedelta(days=random.choice([0, 1, 1, 2, 2, 3, 4, 6, 9])), hoje)
        nasc = date(random.randint(1940, 2024), random.randint(1, 12), random.randint(1, 28))
        sexo = random.choice("MF")
        classi = random.choices(["", "5", "10", "11", "12", "13"], [25, 15, 45, 8, 1, 6])[0]
        rua = titulo(" ".join(x for x in (e["NOM_TIPO_SEGLOGR"], e["NOM_TITULO_SEGLOGR"], e["NOM_SEGLOGR"]) if x))
        sim = lambda p: "1" if random.random() < p else "2"
        linhas.append({
            "id_registro": str(uuid.uuid4()), "salvo_em": f"{notif.isoformat()}T12:00:00.000Z",
            "tp_not": "2", "agravo": "2" if classi == "13" else "1", "dt_notific": notif.isoformat(),
            "sg_uf_not": "PR", "id_municip": "Uniflor", "cod_mun_not": "4128302", "id_unidade": "Unidade Teste",
            "dt_sin_pri": inicio.isoformat(), "nm_pacient": f"Paciente Teste {i:03d}", "dt_nasc": nasc.isoformat(),
            "cs_sexo": sexo, "cs_gestant": "6" if sexo == "M" else "5", "cs_raca": random.choice("12459"),
            "sg_uf": "PR", "id_mn_resi": "Uniflor", "nm_bairro": titulo(e["DSC_LOCALIDADE"]), "nm_logrado": rua,
            "end_na_lista": "1", "nu_numero": e["NUM_ENDERECO"] if e["NUM_ENDERECO"] != "0" else "S/N",
            "latitude": e["LATITUDE"], "longitude": e["LONGITUDE"],
            "geo_metodo": "1" if e["NUM_ENDERECO"] != "0" else "4", "geo_setor": e["COD_SETOR"],
            "febre": sim(.95), "mialgia": sim(.8), "cefaleia": sim(.8), "exantema": sim(.4), "vomito": sim(.3),
            "nausea": sim(.4), "artralgia": sim(.9 if classi == "13" else .2), "dor_retro": sim(.4),
            "hospitaliz": random.choices(["1", "2"], [12 if classi in ("11", "12") else 2, 98])[0],
            "classi_fin": classi, "criterio": "" if not classi else random.choice("12"),
            "evolucao": "" if not classi else random.choices(["1", "2"], [999, 1 if classi == "12" else 0])[0],
        })
    with open(saida, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, delimiter=";")
        w.writeheader()
        w.writerows(linhas)
    print(f"{n} fichas fictícias gravadas em {saida}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    saida = sys.argv[2] if len(sys.argv) > 2 else str(RAIZ / "dados" / "teste" / "fichas_ficticias.csv")
    (RAIZ / "dados" / "teste").mkdir(parents=True, exist_ok=True)
    main(n, saida)
