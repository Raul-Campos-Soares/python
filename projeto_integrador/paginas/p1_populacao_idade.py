"""Página 1 — População por idade e sexo (Projeções da População, Revisão 2024, IBGE).

Estatística descritiva da distribuição de idade (média, mediana, moda, quartis, IQR, desvio padrão)
e comparação entre as 27 UFs (boxplot, ranking, outliers pela regra 1,5·IQR).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ui
from estatistica import outliers, resumo, resumo_ponderado
from geo import REGIOES, UFS

RAIZ = Path(__file__).resolve().parent.parent
ARQ = RAIZ / "dados" / "projecoes_2024_tab1_idade_simples.csv"
AZUL, LARANJA, CINZA = "#2A5FA5", "#D9772B", "#6B7280"
UF_NOMES = {v[0]: v[1] for v in UFS.values()}          # nome da UF -> região
LOCAIS = ["Brasil"] + REGIOES + [v[0] for v in UFS.values()]
br = ui.br


# ------------------------------------------------------------------ dados
@st.cache_data(show_spinner="Lendo as projeções do IBGE...")
def carregar(caminho):
    df = pd.read_csv(caminho, header=5, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    anos = [int(c) for c in df.columns if c.isdigit()]
    for a in anos:
        df[str(a)] = pd.to_numeric(df[str(a)].str.replace(r"[,\s]", "", regex=True), errors="coerce")
    df["IDADE"] = pd.to_numeric(df["IDADE"], errors="coerce")
    df = df.dropna(subset=["LOCAL", "IDADE"])
    df["IDADE"] = df["IDADE"].astype(int)
    return df[["IDADE", "SEXO", "LOCAL"] + [str(a) for a in anos]], anos


@st.cache_data
def matriz(caminho, ano, sexo):
    """População por LOCAL (linhas) x idade simples (colunas) para um ano e sexo."""
    df, _ = carregar(caminho)
    d = df[df["SEXO"] == sexo]
    return d.pivot(index="LOCAL", columns="IDADE", values=str(ano))


def indicadores(M):
    """Indicadores da distribuição de idade de cada linha de M (população por idade simples)."""
    x = M.columns.to_numpy(float)
    w = np.nan_to_num(M.to_numpy(float))
    tot = w.sum(axis=1)
    cum = np.cumsum(w, axis=1) / tot[:, None]

    def q(p):
        return x[(cum >= p - 1e-12).argmax(axis=1)]

    media = (w * x).sum(axis=1) / tot
    jovens, idosos = w[:, x <= 14].sum(axis=1), w[:, x >= 65].sum(axis=1)
    ativos = w[:, (x >= 15) & (x <= 64)].sum(axis=1)
    return pd.DataFrame({
        "populacao": tot, "media": media, "mediana": q(.5), "q1": q(.25), "q3": q(.75),
        "desvio_padrao": np.sqrt((w * (x - media[:, None]) ** 2).sum(axis=1) / tot),
        "pct_0_14": jovens / tot * 100, "pct_60mais": w[:, x >= 60].sum(axis=1) / tot * 100,
        "razao_dependencia": (jovens + idosos) / ativos * 100,
    }, index=M.index).assign(iqr=lambda t: t["q3"] - t["q1"])


@st.cache_data(show_spinner="Calculando a série 2000–2070...")
def serie_completa(caminho, sexo):
    _, anos = carregar(caminho)
    partes = [indicadores(matriz(caminho, a, sexo)).assign(ano=a).reset_index() for a in anos]
    return pd.concat(partes, ignore_index=True)


# ------------------------------------------------------------------ filtros
if not ARQ.exists():
    st.error(f"Arquivo não encontrado: {ARQ.name}. Coloque-o na pasta `dados/`.")
    st.stop()
_, anos = carregar(ARQ)

st.sidebar.header("🔎 Filtros")
local = st.sidebar.selectbox("Território", LOCAIS)
ano = st.sidebar.selectbox("Ano", anos, index=anos.index(2024) if 2024 in anos else 0)
sexo = st.sidebar.radio("Sexo", ["Ambos", "Homens", "Mulheres"])
ano_cmp = st.sidebar.selectbox("Comparar pirâmide com o ano", [a for a in anos if a != ano],
                               index=0)

M = matriz(ARQ, ano, sexo)
ind = indicadores(M)
vet = M.loc[local]
r = resumo_ponderado(vet.index, vet.values)
if r is None:
    st.warning("Sem dados para essa combinação.")
    st.stop()
i = ind.loc[local]

# ------------------------------------------------------------------ cabeçalho
st.title("👥 População por idade e sexo")
st.caption("Fonte: IBGE, Projeções da População, Revisão 2024 (idade simples, 2000–2070). "
           "Anos após o Censo 2022 são projeções. A idade 90 representa 90 anos ou mais.")

k = st.columns(5)
k[0].metric(f"População · {local}, {ano}", br(r["total"]))
k[1].metric("Idade média", f"{br(r['media'], 1)} anos")
k[2].metric("Idade mediana", f"{br(r['mediana'], 0)} anos")
k[3].metric("IQR (Q3 − Q1)", f"{br(r['iqr'], 0)} anos")
k[4].metric("Desvio padrão", f"{br(r['desvio_padrao'], 1)} anos")
k2 = st.columns(5)
k2[0].metric("Q1", f"{br(r['q1'], 0)} anos")
k2[1].metric("Q3", f"{br(r['q3'], 0)} anos")
k2[2].metric("Moda (idade mais comum)", f"{br(r['moda'], 0)} anos")
k2[3].metric("% com 0–14 anos", f"{br(i['pct_0_14'], 1)}%")
k2[4].metric("% com 60 anos ou mais", f"{br(i['pct_60mais'], 1)}%")

aba1, aba2, aba3, aba4, aba5 = st.tabs(
    ["📊 Distribuição por idade", "🔺 Pirâmide etária", "🗺️ Comparação entre UFs", "📈 Evolução 2000–2070",
     "📐 Estatísticas"])

# ------------------------------------------------------------------ distribuição
with aba1:
    d = pd.DataFrame({"idade": vet.index, "populacao": vet.values})
    fig = px.bar(d, x="idade", y="populacao", title=f"População por idade — {local}, {ano} ({sexo})",
                 labels={"idade": "Idade (anos)", "populacao": "População"}, color_discrete_sequence=[AZUL])
    fig.add_vline(x=r["media"], line_color="red", annotation_text="Média")
    fig.add_vline(x=r["mediana"], line_color="green", annotation_text="Mediana", annotation_position="bottom right")
    ui.grafico(fig)
    lado = "acima" if r["media"] > r["mediana"] else "abaixo" if r["media"] < r["mediana"] else "igual à"
    cauda = ("a cauda de idades mais altas puxa a média para cima (assimetria à direita)" if r["media"] > r["mediana"]
             else "a média e a mediana praticamente coincidem" if r["media"] == r["mediana"]
             else "a cauda de idades mais baixas puxa a média para baixo (assimetria à esquerda)")
    st.info(f"**Leitura:** em {ano}, metade da população de {local} tem até {br(r['mediana'], 0)} anos "
            f"(mediana) e a média é {br(r['media'], 1)} anos, {lado} da mediana: {cauda}. "
            f"A idade mais frequente (moda) é {br(r['moda'], 0)} anos. A metade central da população tem entre "
            f"{br(r['q1'], 0)} e {br(r['q3'], 0)} anos (IQR = {br(r['iqr'], 0)} anos).")

# ------------------------------------------------------------------ pirâmide
with aba2:
    H, Mu = matriz(ARQ, ano, "Homens").loc[local], matriz(ARQ, ano, "Mulheres").loc[local]
    H2, M2 = matriz(ARQ, ano_cmp, "Homens").loc[local], matriz(ARQ, ano_cmp, "Mulheres").loc[local]
    tot, tot2 = H.sum() + Mu.sum(), H2.sum() + M2.sum()
    idades = list(H.index)
    fig = go.Figure()
    fig.add_bar(y=idades, x=-(H / tot * 100), orientation="h", name="Homens", marker_color=AZUL,
                customdata=H.values, hovertemplate="Homens %{y} anos: %{customdata:,.0f}<extra></extra>")
    fig.add_bar(y=idades, x=Mu / tot * 100, orientation="h", name="Mulheres", marker_color=LARANJA,
                customdata=Mu.values, hovertemplate="Mulheres %{y} anos: %{customdata:,.0f}<extra></extra>")
    fig.add_scatter(y=idades, x=-(H2 / tot2 * 100), mode="lines", name=f"Homens {ano_cmp}",
                    line=dict(color="black", dash="dot", width=1.5))
    fig.add_scatter(y=idades, x=M2 / tot2 * 100, mode="lines", name=f"Mulheres {ano_cmp}",
                    line=dict(color="black", dash="dot", width=1.5), showlegend=False)
    lim = float(np.ceil(max((H / tot * 100).max(), (Mu / tot * 100).max(), (H2 / tot2 * 100).max(),
                            (M2 / tot2 * 100).max())))
    ticks = np.linspace(-lim, lim, 2 * int(lim) + 1)
    fig.update_layout(barmode="overlay", bargap=0.05, height=560,
                      title=f"Pirâmide etária — {local}, {ano} (linha pontilhada: {ano_cmp})",
                      yaxis_title="Idade (anos)", xaxis_title="% da população total do território",
                      xaxis=dict(tickvals=ticks, ticktext=[f"{abs(t):.0f}%" for t in ticks]))
    ui.grafico(fig)
    ii = indicadores(pd.DataFrame([H + Mu, H2 + M2], index=[ano, ano_cmp]))
    ic, ic2 = ii.iloc[0], ii.iloc[1]
    st.info(f"**Leitura:** de {ano_cmp} para {ano}, a idade mediana de {local} foi de {br(ic2['mediana'], 0)} para "
            f"{br(ic['mediana'], 0)} anos e a parcela com 60 anos ou mais, de {br(ic2['pct_60mais'], 1)}% para "
            f"{br(ic['pct_60mais'], 1)}%. A razão de dependência (jovens + idosos para cada 100 pessoas de 15 a 64 anos) "
            f"foi de {br(ic2['razao_dependencia'], 1)} para {br(ic['razao_dependencia'], 1)}.")

# ------------------------------------------------------------------ comparação UFs
with aba3:
    ufs_ind = ind.loc[[u for u in ind.index if u in UF_NOMES]].copy()
    ufs_ind["regiao"] = ufs_ind.index.map(UF_NOMES)
    ufs_ind = ufs_ind.reset_index().rename(columns={"LOCAL": "UF"})
    opcoes = {"Idade mediana (anos)": "mediana", "Idade média (anos)": "media",
              "% com 60 anos ou mais": "pct_60mais", "% com 0–14 anos": "pct_0_14",
              "Razão de dependência": "razao_dependencia", "Desvio padrão da idade (anos)": "desvio_padrao"}
    nome_ind = st.selectbox("Indicador", list(opcoes))
    col = opcoes[nome_ind]
    st.caption(f"{nome_ind} nas 27 UFs — {ano}, sexo: {sexo}.")
    rs = resumo(ufs_ind[col])
    a = st.columns(5)
    a[0].metric("Média das UFs", br(rs["media"], 1))
    a[1].metric("Mediana das UFs", br(rs["mediana"], 1))
    a[2].metric("IQR", br(rs["iqr"], 1))
    a[3].metric("Amplitude", br(rs["amplitude"], 1))
    a[4].metric("Desvio padrão", br(rs["desvio_padrao"], 1))

    ordem = ufs_ind.sort_values(col)
    fig = px.bar(ordem, x=col, y="UF", orientation="h", color="regiao", labels={col: nome_ind, "regiao": "Região"},
                 title=f"Ranking das UFs — {nome_ind}", height=720)
    fig.add_vline(x=rs["mediana"], line_dash="dash", annotation_text="Mediana das UFs")
    ui.grafico(fig)

    fig = px.box(ufs_ind, x="regiao", y=col, color="regiao", points="all", hover_name="UF",
                 category_orders={"regiao": REGIOES}, labels={col: nome_ind, "regiao": "Região"},
                 title="Boxplot por região (cada ponto é uma UF)")
    ui.grafico(fig)

    fora = outliers(ufs_ind, col, "UF")
    if fora.empty:
        st.success(f"Nenhum outlier pela regra 1,5·IQR (limites: {br(rs['lim_inf'], 1)} a {br(rs['lim_sup'], 1)}).")
    else:
        st.warning("Outliers (1,5·IQR): " + ", ".join(f"{u} ({br(v, 1)})" for u, v in fora.values))
    top, base = ordem.iloc[-1], ordem.iloc[0]
    dif = rs["media"] - rs["mediana"]
    st.info(f"**Leitura:** {top['UF']} tem o maior valor ({br(top[col], 1)}) e {base['UF']}, o menor ({br(base[col], 1)}). "
            f"A média das UFs ({br(rs['media'], 2)}) está {'acima' if dif > 0 else 'abaixo'} da mediana "
            f"({br(rs['mediana'], 2)}) por {br(abs(dif), 2)}; a diferença indica "
            f"{'pouca' if abs(dif) < 0.1 * rs['desvio_padrao'] else 'alguma'} assimetria entre os estados.")

# ------------------------------------------------------------------ evolução
with aba4:
    serie = serie_completa(ARQ, sexo)
    escolha = st.multiselect("Territórios", LOCAIS, default=[local] if local == "Brasil" else [local, "Brasil"])
    met = st.radio("Indicador", ["Idade mediana", "Idade média", "% com 60 anos ou mais", "Razão de dependência"],
                   horizontal=True)
    mcol = {"Idade mediana": "mediana", "Idade média": "media", "% com 60 anos ou mais": "pct_60mais",
            "Razão de dependência": "razao_dependencia"}[met]
    s = serie[serie["LOCAL"].isin(escolha)]
    if s.empty:
        st.info("Escolha ao menos um território.")
    else:
        fig = px.line(s, x="ano", y=mcol, color="LOCAL", labels={mcol: met, "ano": "Ano", "LOCAL": "Território"},
                      title=f"{met}, 2000–2070 (sexo: {sexo})")
        fig.add_vline(x=2022, line_dash="dot", annotation_text="Censo 2022")
        fig.add_vline(x=ano, line_dash="dash", line_color="red", annotation_text=str(ano))
        ui.grafico(fig)
        st.caption("A linha pontilhada marca o Censo 2022; à direita estão as projeções.")

# ------------------------------------------------------------------ estatísticas
with aba5:
    st.subheader(f"Medidas da distribuição de idade — {local}, {ano}, {sexo}")
    medidas = pd.DataFrame({
        "Medida": ["Média", "Mediana", "Moda", "Q1", "Q3", "IQR", "Amplitude", "Desvio padrão", "Variância",
                   "Limite inferior (Q1−1,5·IQR)", "Limite superior (Q3+1,5·IQR)"],
        "Valor": [r["media"], r["mediana"], r["moda"], r["q1"], r["q3"], r["iqr"], r["amplitude"],
                  r["desvio_padrao"], r["variancia"], r["lim_inf"], r["lim_sup"]]})
    medidas["Valor"] = medidas["Valor"].map(lambda v: br(v, 2))
    ui.tabela(medidas, hide_index=True)
    fora_idade = vet[(vet.index < r["lim_inf"]) | (vet.index > r["lim_sup"])]
    st.markdown(
        f"Pela regra 1,5·IQR, idades fora de [{br(r['lim_inf'], 1)} ; {br(r['lim_sup'], 1)}] seriam consideradas "
        f"atípicas: {'nenhuma idade está fora (a distribuição de idades cobre todo o intervalo de 0 a 90 anos).' if fora_idade.empty else str(len(fora_idade)) + ' idades.'}")
    with st.expander("Como foram calculadas (para a apresentação)"):
        st.markdown("""
- Os dados vêm **agrupados por idade simples** (0 a 90): cada idade é um valor e a população é a sua frequência.
- **Média** = soma(idade × população) ÷ população total. **Mediana, Q1 e Q3** = menor idade em que a frequência acumulada atinge 50%, 25% e 75%.
- **Moda** = idade com maior população. **IQR** = Q3 − Q1. **Amplitude** = maior − menor idade (0 a 90).
- **Variância** = soma(população × (idade − média)²) ÷ população total (população inteira, divisor *n*); **desvio padrão** = raiz da variância.
- A idade 90 reúne 90 anos ou mais, o que subestima levemente a média.
- Na aba *Comparação entre UFs* as estatísticas (média, mediana, IQR, desvio padrão com divisor *n−1*) são calculadas sobre os 27 valores estaduais.
""")
    st.subheader(f"Regiões — {ano}")
    reg = ind.loc[[x for x in REGIOES if x in ind.index], ["populacao", "media", "mediana", "iqr", "desvio_padrao",
                                                           "pct_60mais"]].reset_index()
    reg.columns = ["Região", "População", "Idade média", "Idade mediana", "IQR", "Desvio padrão", "% 60+"]
    for c in reg.columns[1:]:
        reg[c] = reg[c].map(lambda v: br(v, 1 if c != "População" else 0))
    ui.tabela(reg, hide_index=True)
