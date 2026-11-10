"""ETL da Tabela 4709 do SIDRA (Censo 2010 x 2022) — usado pela página "Crescimento demográfico".

O CSV bruto do SIDRA traz três blocos (população 2022, variação absoluta desde 2010 compatibilizada
e taxa geométrica de crescimento), cada um com Brasil, regiões, UFs, regiões geográficas e municípios.
`extrair` lê os blocos; `tratar` fica só com os municípios e calcula as métricas.
"""
import csv
import re

import pandas as pd

from geo import CAPITAIS, REGIOES, UF_REGIAO  # noqa: F401  (REGIOES é usado pelo app)

PERSONAS = ["Curitiba", "Porto Alegre", "Belo Horizonte", "Salvador", "Florianópolis"]
ANOS_ENTRE_CENSOS = 12  # 1/ago/2010 -> 1/ago/2022 (mesma convenção do IBGE para a taxa geométrica)
_MUN = re.compile(r"^(.*)\s\(([A-Z]{2})\)$")


def _num(txt):
    """Converte texto do SIDRA em número; símbolos ('-', 'X', '..', '...') viram NaN."""
    t = str(txt).strip().replace(".", "").replace(",", ".") if "," in str(txt) else str(txt).strip()
    try:
        return float(t)
    except ValueError:
        return float("nan")


def extrair(caminho):
    """Lê o CSV bruto e devolve um DataFrame com: nome, populacao_2022, variacao_abs, taxa_ibge_pct."""
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.reader(f, delimiter=";"))
    blocos, atual, nome_var = {}, None, None
    for lin in linhas:
        if not lin:
            continue
        c0 = lin[0].strip()
        if c0.startswith("Variável -"):
            nome_var, atual = c0, []
            blocos[nome_var] = atual
        elif c0.startswith("Fonte:"):
            atual = None
        elif atual is not None and len(lin) >= 2 and not c0.startswith(("Brasil, Grande", "Tabela")):
            atual.append((c0, lin[1]))
    chaves = {"pop": "População residente", "var": "Variação absoluta", "tx": "Taxa de crescimento"}
    achados = {k: next((b for n, b in blocos.items() if v in n), None) for k, v in chaves.items()}
    if achados["pop"] is None or achados["var"] is None:
        raise ValueError("O arquivo não parece ser a Tabela 4709 do SIDRA (faltam os blocos de população/variação).")
    n = len(achados["pop"])
    if len(achados["var"]) != n:
        raise ValueError("Os blocos do CSV têm tamanhos diferentes; exporte a tabela novamente do SIDRA.")
    df = pd.DataFrame({
        "nome": [a for a, _ in achados["pop"]],
        "populacao_2022": [_num(v) for _, v in achados["pop"]],
        "variacao_abs": [_num(v) for _, v in achados["var"]],
    })
    df["taxa_ibge_pct"] = [_num(v) for _, v in achados["tx"]] if achados["tx"] and len(achados["tx"]) == n else float("nan")
    return df


def tratar(bruto):
    """Fica só com municípios ('Nome (UF)') e calcula população 2010, crescimento e taxa anual."""
    m = bruto["nome"].str.extract(_MUN)
    d = bruto.assign(municipio=m[0], uf=m[1]).dropna(subset=["municipio", "uf"]).copy()
    d = d.dropna(subset=["populacao_2022", "variacao_abs"])
    d = d.rename(columns={"populacao_2022": "pop_2022"})
    d["pop_2010"] = d["pop_2022"] - d["variacao_abs"]
    d = d[d["pop_2010"] > 0].copy()
    d["regiao"] = d["uf"].map(UF_REGIAO)
    d["cresc_acum_pct"] = d["variacao_abs"] / d["pop_2010"] * 100
    d["taxa_anual_calc_pct"] = ((d["pop_2022"] / d["pop_2010"]) ** (1 / ANOS_ENTRE_CENSOS) - 1) * 100
    d["eh_capital"] = [CAPITAIS.get(u) == mun for u, mun in zip(d["uf"], d["municipio"])]
    cols = ["municipio", "uf", "regiao", "pop_2010", "pop_2022", "variacao_abs",
            "cresc_acum_pct", "taxa_anual_calc_pct", "taxa_ibge_pct", "eh_capital"]
    for c in cols:
        if c not in d:
            d[c] = float("nan")
    return d[cols].reset_index(drop=True)
