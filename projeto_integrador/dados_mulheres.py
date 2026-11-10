"""Dados da página "Mulheres": Censo 2022, população por sexo e grupo de idade (SIDRA, tabela 9514).

Caminhos para obter a base (a página tenta nesta ordem):
  1. CSV em dados/ gerado por `python baixar_dados_mulheres.py` (funciona offline depois);
  2. arquivo enviado pela barra lateral;
  3. download direto da API oficial do IBGE (precisa de internet).
"""
import io
import re
import unicodedata

import numpy as np
import pandas as pd
import requests

from geo import REGIOES, UFS  # noqa: F401  (usados pelo app)

URL_API = ("https://apisidra.ibge.gov.br/values/t/9514/n3/all/v/allxp/p/all/c2/all/c286/113635/c287/all")
URL_API_ALT = "https://apisidra.ibge.gov.br/values/t/9514/n3/all/v/allxp/p/all/c2/all/c287/all"


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


_NOME2UF = {_norm(v[0]): k for k, v in UFS.items()}
_MUN = re.compile(r"^(.*?)\s*(?:\(|-\s*)([A-Z]{2})\)?$")


# ------------------------------------------------------------------ idade -> faixa quinquenal
def _limites(nome):
    """Devolve (inicio, fim) de um rótulo de idade do SIDRA, ou None se não for uma idade."""
    n = _norm(nome)
    if n.startswith("menos de 1"):
        return (0, 0)
    m = re.match(r"^(\d+) a (\d+) anos?$", n)
    if m:
        return int(m[1]), int(m[2])
    m = re.match(r"^(\d+) anos? ou mais$", n)
    if m:
        return int(m[1]), 999
    m = re.match(r"^(\d+) anos?$", n)
    if m:
        return int(m[1]), int(m[1])
    return None


def _rotulo(ini):
    return "100 anos ou mais" if ini >= 100 else f"{ini} a {ini + 4} anos"


def _faixas_de(idades):
    """Mapeia rótulos de idade em faixas de 5 anos. Usa as faixas prontas; se não houver, agrega idades simples."""
    lim = {i: _limites(i) for i in idades}
    prontas = {i: _rotulo(l[0]) for i, l in lim.items() if l and l[1] - l[0] == 4 and l[0] % 5 == 0}
    if l100 := [i for i, l in lim.items() if l and l[0] == 100 and l[1] == 999]:
        prontas[l100[0]] = _rotulo(100)
    if len(prontas) >= 5:
        return prontas
    return {i: _rotulo((l[0] // 5) * 5) for i, l in lim.items() if l and l[0] == l[1] or (l and l[1] == 999)}


def age_groups(t):
    """Faixas quinquenais presentes na base, em ordem crescente."""
    f = [x for x in t["faixa"].unique() if x != "Total"]
    return sorted(f, key=lambda x: int(re.match(r"\d+", x)[0]))


# ------------------------------------------------------------------ leitura
def _raw_de_tabela(df):
    """Padroniza qualquer tabela com colunas de território, sexo, idade, ano e valor."""
    cols = {_norm(c): c for c in df.columns}

    def acha(*chaves):
        for k, c in cols.items():
            if any(ch in k for ch in chaves):
                return c
        return None

    terr = acha("territorio", "unidade da federa", "munic", "local")
    sexo, idade = acha("sexo"), acha("idade")
    ano, valor = acha("ano"), acha("valor", "pessoas", "populacao")
    if not (terr and sexo and valor):
        raise ValueError("Não reconheci as colunas. Gere o arquivo com `python baixar_dados_mulheres.py` "
                         "(colunas: territorio, ano, sexo, idade, valor).")
    raw = pd.DataFrame({
        "territorio": df[terr], "sexo": df[sexo],
        "idade": df[idade] if idade else "Total",
        "ano": df[ano] if ano else 2022,
        "valor": df[valor],
    })
    return raw


def read_bytes(nome, conteudo):
    """Lê um CSV/XLSX (arquivo local ou enviado pelo usuário)."""
    if nome.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(conteudo))
    else:
        txt = conteudo.decode("utf-8-sig", errors="replace")
        df = pd.read_csv(io.StringIO(txt), sep=None, engine="python", dtype=str)
    return _raw_de_tabela(df)


def _api_para_raw(dados):
    """Converte o JSON da API do SIDRA (lista; 1º item = descrição das colunas) em tabela padronizada."""
    if not isinstance(dados, list) or len(dados) < 2:
        raise ValueError("Resposta vazia da API do SIDRA.")
    cab, linhas = dados[0], dados[1:]
    desc = {k: _norm(v) for k, v in cab.items()}
    nome_col = {d: k for k, d in desc.items() if re.fullmatch(r"d\d+n", k.lower())}

    def acha(palavra):  # palavra inteira ("idade" não casa com "unidade")
        return next((k for d, k in nome_col.items() if re.search(rf"\b{palavra}\b", d)), None)

    k_sexo, k_ano, k_var, k_forma = acha("sexo"), acha("ano"), acha("variavel"), acha("forma")
    k_ida = next((k for d, k in nome_col.items() if re.search(r"\bidade\b", d) and "forma" not in d), None)
    ocupadas = {k_sexo, k_ano, k_var, k_forma, k_ida}
    k_terr = next((k for k in nome_col.values() if k not in ocupadas), None)
    if not all([k_sexo, k_ida, k_terr]):
        raise ValueError(f"Estrutura inesperada na resposta da API: {list(cab.values())}")
    df = pd.DataFrame(linhas)
    if k_forma:
        df = df[df[k_forma].map(_norm) == "total"]
    if k_var:
        df = df[df[k_var].map(_norm).str.contains("populacao residente")]
    if "MN" in df and (df["MN"].map(_norm) == "pessoas").any():
        df = df[df["MN"].map(_norm) == "pessoas"]
    return pd.DataFrame({
        "territorio": df[k_terr], "sexo": df[k_sexo], "idade": df[k_ida],
        "ano": df[k_ano] if k_ano else 2022, "valor": df["V"],
    })


def fetch_sidra(timeout=180):
    """Baixa da API oficial do IBGE a tabela 9514 (UFs, 2022, sexo x idade)."""
    ultimo = None
    for url in (URL_API, URL_API_ALT):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            return _api_para_raw(r.json())
        except (requests.RequestException, ValueError) as e:
            ultimo = e
    raise ultimo


# ------------------------------------------------------------------ preparo
def _sexo(v):
    n = _norm(v)
    if n.startswith(("home", "masc")):
        return "Homens"
    if n.startswith(("mulher", "fem")):
        return "Mulheres"
    if n == "total":
        return "Total"
    return None


def prepare(raw):
    """Devolve a base "tidy": ano, nivel, territorio, uf, regiao, sexo, faixa, valor."""
    d = raw.copy()
    d["sexo"] = d["sexo"].map(_sexo)
    d = d.dropna(subset=["sexo"])
    v = d["valor"].astype(str).str.strip()
    v = v.str.replace(r"\.(?=\d{3}(\D|$))", "", regex=True).str.replace(",", ".", regex=False)
    d["valor"] = pd.to_numeric(v.replace({"-": "0"}), errors="coerce")
    d["ano"] = pd.to_numeric(d["ano"], errors="coerce").astype("Int64")
    d = d.dropna(subset=["valor", "ano", "territorio"])
    d["ano"] = d["ano"].astype(int)

    # território -> UF (nível "UF") ou município "Nome (UF)" / "Nome - UF"
    nivel, nome, uf = [], [], []
    for t in d["territorio"].astype(str):
        if _norm(t) in _NOME2UF:
            s = _NOME2UF[_norm(t)]
            nivel.append("UF"); nome.append(UFS[s][0]); uf.append(s)
        elif (m := _MUN.match(t.strip())) and m[2] in UFS:
            nivel.append("Município"); nome.append(m[1].strip()); uf.append(m[2])
        else:
            nivel.append(None); nome.append(None); uf.append(None)
    d["nivel"], d["territorio"], d["uf"] = nivel, nome, uf
    d = d.dropna(subset=["nivel"])
    d["regiao"] = d["uf"].map(lambda s: UFS[s][1])

    idades = d["idade"].astype(str).unique()
    mapa = _faixas_de(idades)
    faixa = d["idade"].astype(str).map(mapa).astype(object)
    d["faixa"] = faixa.where(d["idade"].astype(str).map(_norm) != "total", "Total")
    d = d.dropna(subset=["faixa"])
    t = (d.groupby(["ano", "nivel", "territorio", "uf", "regiao", "sexo", "faixa"], as_index=False)["valor"].sum())
    if t.empty:
        raise ValueError("Nenhuma linha válida após o tratamento (confira UFs, sexo e idade no arquivo).")
    return t


def _mediana_agrupada(freq, ini):
    """Mediana de dados agrupados em faixas de 5 anos (interpolação linear). freq: matriz territórios x faixas."""
    tot = freq.sum(axis=1)
    cum = np.cumsum(freq, axis=1)
    pos = (cum >= (tot / 2)[:, None]).argmax(axis=1)
    out = np.full(len(tot), np.nan)
    for i, p in enumerate(pos):
        if tot[i] <= 0:
            continue
        antes = cum[i, p - 1] if p > 0 else 0.0
        f = freq[i, p]
        out[i] = ini[p] + (tot[i] / 2 - antes) / f * 5 if f > 0 else ini[p]
    return out


def build_base(t, grupos_sel, has_age):
    """Uma linha por (ano, território) com Homens, Mulheres, Total, % mulheres, razão de sexo,
    e (se houver idade) % de idosas (60+) e idade mediana das mulheres — estes dois usam todas as faixas."""
    chave = ["ano", "nivel", "territorio", "uf", "regiao"]
    hm = t[t["sexo"].isin(["Homens", "Mulheres"])]
    sel = hm[hm["faixa"].isin(grupos_sel)] if has_age else hm[hm["faixa"] == "Total"]
    p = sel.pivot_table(index=chave, columns="sexo", values="valor", aggfunc="sum").reset_index()
    p.columns.name = None
    for c in ("Homens", "Mulheres"):
        if c not in p:
            p[c] = np.nan
    p["Total"] = p["Homens"] + p["Mulheres"]
    p["pct_mulheres"] = p["Mulheres"] / p["Total"] * 100
    p["razao_sexo"] = p["Homens"] / p["Mulheres"] * 100
    if has_age:
        grupos = age_groups(t)
        ini = np.array([int(re.match(r"\d+", g)[0]) for g in grupos])
        f = hm[(hm["sexo"] == "Mulheres") & hm["faixa"].isin(grupos)].pivot_table(
            index=chave, columns="faixa", values="valor", aggfunc="sum").reindex(columns=grupos).fillna(0)
        mat = f.to_numpy()
        idosas = mat[:, ini >= 60].sum(axis=1) / mat.sum(axis=1) * 100
        extra = f.reset_index()[chave].assign(pct_idosas=idosas, idade_med_f=_mediana_agrupada(mat, ini))
        p = p.merge(extra, on=chave, how="left")
    return p


def describe(s):
    """Estatística descritiva de uma série (valores numéricos, prontos para tabela)."""
    s = pd.Series(s).dropna().astype(float)
    q1, med, q3 = s.quantile([.25, .5, .75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    fora = (s < lo) | (s > hi)
    r1 = s.round(1)
    moda = float(r1.mode().iloc[0]) if len(r1) and r1.value_counts().iloc[0] > 1 else np.nan
    media = float(s.mean())
    dp = float(s.std()) if len(s) > 1 else np.nan
    return {
        "Média": media, "Mediana": float(med), "Moda": moda, "Q1": float(q1), "Q3": float(q3), "IQR": float(iqr),
        "Amplitude": float(s.max() - s.min()), "Variância": float(s.var()) if len(s) > 1 else np.nan,
        "Desvio padrão": dp, "Coef. variação (%)": dp / media * 100 if media else np.nan,
        "Limite inferior": float(lo), "Limite superior": float(hi), "Nº outliers": float(fora.sum()),
        "Média sem outliers": float(s[~fora].mean()) if (~fora).any() else np.nan, "n": float(len(s)),
    }
