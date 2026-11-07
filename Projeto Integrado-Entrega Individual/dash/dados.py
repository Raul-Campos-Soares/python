# -*- coding: utf-8 -*-
"""Ingestão (ETL) e estatística descritiva – Mulheres no Brasil (Censo 2022, SIDRA tabela 9514)."""
import csv
import io
import re
import unicodedata

import numpy as np
import pandas as pd
import requests

# sigla: (nome, região, código IBGE)
UFS = {
    "RO": ("Rondônia", "Norte", 11), "AC": ("Acre", "Norte", 12), "AM": ("Amazonas", "Norte", 13),
    "RR": ("Roraima", "Norte", 14), "PA": ("Pará", "Norte", 15), "AP": ("Amapá", "Norte", 16),
    "TO": ("Tocantins", "Norte", 17),
    "MA": ("Maranhão", "Nordeste", 21), "PI": ("Piauí", "Nordeste", 22), "CE": ("Ceará", "Nordeste", 23),
    "RN": ("Rio Grande do Norte", "Nordeste", 24), "PB": ("Paraíba", "Nordeste", 25),
    "PE": ("Pernambuco", "Nordeste", 26), "AL": ("Alagoas", "Nordeste", 27),
    "SE": ("Sergipe", "Nordeste", 28), "BA": ("Bahia", "Nordeste", 29),
    "MG": ("Minas Gerais", "Sudeste", 31), "ES": ("Espírito Santo", "Sudeste", 32),
    "RJ": ("Rio de Janeiro", "Sudeste", 33), "SP": ("São Paulo", "Sudeste", 35),
    "PR": ("Paraná", "Sul", 41), "SC": ("Santa Catarina", "Sul", 42), "RS": ("Rio Grande do Sul", "Sul", 43),
    "MS": ("Mato Grosso do Sul", "Centro-Oeste", 50), "MT": ("Mato Grosso", "Centro-Oeste", 51),
    "GO": ("Goiás", "Centro-Oeste", 52), "DF": ("Distrito Federal", "Centro-Oeste", 53),
}
REGIOES = ["Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"]

SIDRA_URL = ("https://apisidra.ibge.gov.br/values/t/9514/n3/all/v/93/p/2022/"
             "c2/all/c287/all/c286/all")


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.strip().lower()


_NAME2UF = {norm(v[0]): k for k, v in UFS.items()}
_REG_N = {norm(r) for r in REGIOES}


# ------------------------------------------------------------------ leitura
def _num(x):
    s = str(x).strip().replace(" ", "")
    if s in {"", "-", "X", "x", "..", "...", "nan", "None"}:
        return np.nan
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return np.nan


def _rows_to_df(rows):
    hdr = None
    for i, r in enumerate(rows):
        cells = [norm(c) for c in r]
        if sum(1 for c in cells if c) >= 3 and ("sexo" in cells or "mulheres" in cells or "valor" in cells):
            hdr = i
            break
    if hdr is None:
        raise ValueError("Não encontrei o cabeçalho (colunas 'Sexo' e 'Valor', ou 'Homens'/'Mulheres').")
    header, seen = [], {}
    for j, c in enumerate(rows[hdr]):
        c = str(c).strip() or f"col{j}"
        seen[c] = seen.get(c, 0) + 1
        header.append(c if seen[c] == 1 else f"{c}_{seen[c]}")
    body = [(list(r) + [""] * len(header))[: len(header)]
            for r in rows[hdr + 1:] if sum(1 for c in r if str(c).strip()) >= 2]
    return pd.DataFrame(body, columns=header)


def read_bytes(name: str, data: bytes) -> pd.DataFrame:
    """Lê CSV/XLSX exportado do SIDRA (com linhas de título/rodapé) em um DataFrame bruto."""
    if name.lower().endswith((".xlsx", ".xls")):
        raw = pd.read_excel(io.BytesIO(data), header=None, dtype=str).fillna("")
        return _rows_to_df(raw.values.tolist())
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    head = "\n".join(text.splitlines()[:8])
    sep = ";" if head.count(";") >= head.count(",") else ","
    return _rows_to_df(list(csv.reader(io.StringIO(text), delimiter=sep)))


def fetch_sidra() -> pd.DataFrame:
    """Tabela 9514 (Censo 2022) por UF, sexo e idade direto da API do SIDRA."""
    r = requests.get(SIDRA_URL, timeout=90)
    r.raise_for_status()
    js = r.json()
    return pd.DataFrame(js[1:]).rename(columns=js[0])


# ------------------------------------------------------------------ tratamento
def _sexo(x):
    n = norm(x)
    if n.startswith("mulher"):
        return "Mulheres"
    if n.startswith("homen"):
        return "Homens"
    if n.startswith("total"):
        return "Total"
    return None


def _classify(name: str):
    n = norm(name)
    if n == "brasil":
        return "Brasil", "BR"
    if n in _NAME2UF:
        return "UF", _NAME2UF[n]
    if n in _REG_N:
        return "Região", "—"
    m = re.search(r"\(([A-Z]{2})\)\s*$|-\s*([A-Z]{2})\s*$", str(name).strip())
    if m and (m.group(1) or m.group(2)) in UFS:
        return "Município", m.group(1) or m.group(2)
    return "Outro", "—"


def prepare(raw: pd.DataFrame) -> pd.DataFrame:
    """Padroniza qualquer exportação SIDRA para: territorio, nivel, uf, regiao, sexo, faixa, ano, valor."""
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    names = {c: norm(c) for c in df.columns}

    def find(*keys, exclude=()):
        for c, n in names.items():
            if any(k in n for k in keys) and not any(e in n for e in exclude):
                return c
        return None

    c_val = find("valor")
    if c_val is None:  # layout "largo": colunas Total / Homens / Mulheres
        sx = [c for c, n in names.items() if n in ("total", "homens", "mulheres")]
        if not sx:
            raise ValueError("Não achei a coluna 'Valor' nem colunas Homens/Mulheres.")
        ids = [c for c in df.columns if c not in sx]
        df = df.melt(id_vars=ids, value_vars=sx, var_name="Sexo", value_name="Valor")
        names = {c: norm(c) for c in df.columns}
        c_val = "Valor"
    c_sexo = find("sexo")
    c_terr = (find("municipio", exclude=("codigo", "nivel")) or find("unidade da federa", exclude=("codigo",))
              or find("grande regiao", exclude=("codigo",)) or find("territ", exclude=("codigo", "nivel")))
    c_idade = next((c for c, n in names.items() if n.startswith("idade") and "forma" not in n), None)
    c_forma = find("forma de declara")
    c_ano = next((c for c, n in names.items() if n == "ano"), None)
    if not (c_sexo and c_terr):
        raise ValueError("Preciso de colunas de território (UF/Município) e de Sexo.")

    t = pd.DataFrame({
        "territorio": df[c_terr].astype(str).str.strip().replace("", np.nan).ffill(),
        "sexo": df[c_sexo].map(_sexo),
        "faixa": df[c_idade].astype(str).str.strip() if c_idade else "Total",
        "ano": df[c_ano].astype(str).str.strip() if c_ano else "—",
        "valor": df[c_val].map(_num),
    })
    if c_forma:  # evita contar duas vezes (idade em anos x data de nascimento)
        t = t[df[c_forma].map(norm).str.contains("total|idade em anos", regex=True).values | (df[c_forma].map(norm) == "")]
    t = t.dropna(subset=["valor", "sexo", "territorio"])
    cl = t["territorio"].map(_classify)
    t["nivel"] = [c[0] for c in cl]
    t["uf"] = [c[1] for c in cl]
    t = t[t["nivel"] != "Outro"].copy()
    t["regiao"] = np.where(t["nivel"].isin(["UF", "Município"]), t["uf"].map(lambda u: UFS[u][1] if u in UFS else "—"), "—")
    t.loc[t["nivel"] == "UF", "territorio"] = t.loc[t["nivel"] == "UF", "uf"].map(lambda u: UFS[u][0])
    t.loc[t["nivel"] == "Brasil", "regiao"] = "Brasil"
    t["faixa"] = t["faixa"].str.replace(r"\s+", " ", regex=True)
    return t.drop_duplicates(["territorio", "sexo", "faixa", "ano"]).reset_index(drop=True)


def age_groups(t: pd.DataFrame) -> list:
    """Grupos quinquenais ('0 a 4 anos' …) + grupo aberto final, em ordem etária."""
    labs = t["faixa"].unique()
    rng = [f for f in labs if (m := re.fullmatch(r"(\d+) a (\d+) anos", f)) and int(m[2]) - int(m[1]) == 4]
    if not rng:
        return []
    mx = max(int(re.match(r"\d+ a (\d+)", f)[1]) for f in rng)
    openg = [f for f in labs if (m := re.fullmatch(r"(\d+) anos ou mais", f)) and int(m[1]) == mx + 1]
    return sorted(rng + openg, key=lambda f: int(re.match(r"\d+", f)[0]))


def lower_bound(f: str) -> int:
    return int(re.match(r"\d+", f)[0])


# ------------------------------------------------------------------ indicadores
def build_base(t: pd.DataFrame, groups_sel: list, has_age: bool) -> pd.DataFrame:
    """Uma linha por território: mulheres, homens, % mulheres, razão de sexo (+ extras etários)."""
    x = t[t["faixa"].isin(groups_sel)] if has_age else t[t["faixa"] == "Total"]
    x = x[x["sexo"].isin(["Homens", "Mulheres"])]
    p = x.pivot_table(index=["territorio", "nivel", "uf", "regiao", "ano"], columns="sexo",
                      values="valor", aggfunc="sum").reset_index()
    for c in ("Homens", "Mulheres"):
        if c not in p:
            p[c] = np.nan
    p["Total"] = p["Homens"] + p["Mulheres"]
    p["pct_mulheres"] = p["Mulheres"] / p["Total"] * 100
    p["razao_sexo"] = p["Homens"] / p["Mulheres"] * 100
    if has_age:
        ex = _extras(t)
        p = p.merge(ex, on=["territorio", "ano"], how="left")
    return p


def _extras(t: pd.DataFrame) -> pd.DataFrame:
    """% de idosas (60+) entre as mulheres e idade mediana feminina (mediana de dados agrupados)."""
    g = age_groups(t)
    m = t[(t["sexo"] == "Mulheres") & (t["faixa"].isin(g))]
    pv = m.pivot_table(index=["territorio", "ano"], columns="faixa", values="valor", aggfunc="sum")[g].fillna(0)
    arr, low = pv.values, np.array([lower_bound(f) for f in g])
    n = arr.sum(1)
    cum = arr.cumsum(1)
    idx = (cum >= (n / 2)[:, None]).argmax(1)
    rows = np.arange(len(pv))
    prev = np.where(idx > 0, cum[rows, np.maximum(idx - 1, 0)], 0)
    med = low[idx] + (n / 2 - prev) / np.where(arr[rows, idx] == 0, np.nan, arr[rows, idx]) * 5
    idosas = arr[:, low >= 60].sum(1) / np.where(n == 0, np.nan, n) * 100
    return pd.DataFrame({"territorio": pv.index.get_level_values(0), "ano": pv.index.get_level_values(1),
                         "pct_idosas": idosas, "idade_med_f": med})


def describe(s: pd.Series) -> dict:
    """Média, mediana, moda, quartis, IQR, amplitude, variância, desvio padrão e outliers (1,5·IQR)."""
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return {}
    q1, q2, q3 = s.quantile([.25, .5, .75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    out = s[(s < lo) | (s > hi)]
    mode = s.round(1).mode()
    return {"n": len(s), "Média": s.mean(), "Mediana": q2, "Moda (1 casa)": mode.iloc[0] if len(mode) else np.nan,
            "Mínimo": s.min(), "Q1": q1, "Q3": q3, "Máximo": s.max(), "IQR": iqr, "Amplitude": s.max() - s.min(),
            "Variância": s.var(ddof=1) if len(s) > 1 else np.nan, "Desvio padrão": s.std(ddof=1) if len(s) > 1 else np.nan,
            "Coef. variação (%)": s.std(ddof=1) / s.mean() * 100 if len(s) > 1 and s.mean() else np.nan,
            "Limite inferior": lo, "Limite superior": hi, "Nº outliers": len(out),
            "Média sem outliers": s[(s >= lo) & (s <= hi)].mean()}
