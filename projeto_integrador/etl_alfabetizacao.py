"""Leitura e organização da base de alfabetização (Censo 2010 e 2022, IBGE)."""
from pathlib import Path

import pandas as pd

from geo import REGIOES  # noqa: F401

COLUNAS = ["Nivel", "Territorio", "UF", "Regiao", "Ano", "Sexo", "Faixa_Etaria", "Taxa_Alfabetizacao"]


def carregar_base(fonte):
    """`fonte` pode ser um caminho (Path/str) ou um arquivo enviado pelo st.file_uploader."""
    if hasattr(fonte, "getvalue"):
        nome, conteudo = fonte.name.lower(), fonte.getvalue()
        import io
        buf = io.BytesIO(conteudo)
    else:
        nome, buf = str(fonte).lower(), fonte
    if nome.endswith((".xlsx", ".xls")):
        df = pd.read_excel(buf)
    else:
        df = pd.read_csv(buf, sep=None, engine="python", encoding="utf-8-sig")
    faltam = [c for c in COLUNAS if c not in df.columns]
    if faltam:
        raise ValueError(f"colunas ausentes: {faltam}. Esperado: {COLUNAS}")
    df = df[COLUNAS].copy()
    for c in ["Nivel", "Territorio", "UF", "Regiao", "Sexo", "Faixa_Etaria"]:
        df[c] = df[c].astype("string").str.strip()
    df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce").astype("Int64")
    df["Taxa_Alfabetizacao"] = pd.to_numeric(df["Taxa_Alfabetizacao"], errors="coerce")
    df = df.dropna(subset=["Ano", "Taxa_Alfabetizacao"])
    df["Ano"] = df["Ano"].astype(int)
    for c in ["Nivel", "Territorio", "UF", "Regiao", "Sexo", "Faixa_Etaria"]:
        df[c] = df[c].astype(object).where(df[c].notna(), None)
    return df.reset_index(drop=True)


def nivel(df, nome):
    """Linhas de um nível territorial ('Brasil', 'Região' ou 'UF'), só o total por sexo, 15 anos ou mais."""
    return df[(df["Nivel"] == nome) & (df["Sexo"] == "Total") & (df["Faixa_Etaria"] == "15+")].copy()


def evolucao_uf(df):
    """Ganho (em p.p.) da taxa de cada UF entre o primeiro e o último ano da base."""
    u = nivel(df, "UF")
    anos = sorted(u["Ano"].unique())
    if len(anos) < 2:
        return pd.DataFrame()
    a0, a1 = anos[0], anos[-1]
    p = u.pivot_table(index=["UF", "Territorio", "Regiao"], columns="Ano", values="Taxa_Alfabetizacao").reset_index()
    p = p.dropna(subset=[a0, a1]).rename(columns={a0: f"Taxa_{a0}", a1: f"Taxa_{a1}"})
    p["Ganho_pp"] = p[f"Taxa_{a1}"] - p[f"Taxa_{a0}"]
    p.columns.name = None
    return p
