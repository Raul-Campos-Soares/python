"""Página 4 — Crescimento demográfico, Censo 2010 x 2022 (foco em BH e capitais). Fonte: SIDRA, tabela 4709."""
import glob
import io
import os
import tempfile
from urllib.parse import quote

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import etl_crescimento as etl
import ui

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.path.join(AQUI, "dados")
OBRIGATORIAS = ["municipio", "uf", "regiao", "pop_2010", "pop_2022", "variacao_abs",
                "cresc_acum_pct", "taxa_anual_calc_pct", "eh_capital"]
METRICAS = {"Crescimento acumulado 2010–2022 (%)": "cresc_acum_pct",
            "Taxa média anual (% a.a.)": "taxa_anual_calc_pct"}


def n(v, casas=0):
    """Formata número no padrão brasileiro."""
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ------------------------------------------------------------------ Dados (ETL + upload)
def ler_upload(f):
    if f.name.lower().endswith(".xlsx"):
        return pd.read_excel(f)
    txt = f.getvalue().decode("utf-8-sig", errors="replace")
    if txt.lstrip().startswith('"Tabela'):              # CSV bruto do SIDRA -> roda o ETL
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as t:
            t.write(txt)
        return etl.tratar(etl.extrair(t.name))
    return pd.read_csv(io.StringIO(txt), sep=None, engine="python")


@st.cache_data(show_spinner="Tratando o arquivo do IBGE...")
def base_padrao():
    """Sem upload: procura o CSV bruto do SIDRA (tabela4709*.csv) na pasta do app e roda o ETL sozinho.
    Se não achar, usa a base_tratada.csv."""
    brutos = sorted(glob.glob(os.path.join(DADOS, "tabela4709*.csv")))
    if brutos:
        return etl.tratar(etl.extrair(brutos[0]))
    caminho = os.path.join(DADOS, "base_tratada.csv")
    return pd.read_csv(caminho) if os.path.exists(caminho) else None


st.sidebar.header("📂 Dados")
up = st.sidebar.file_uploader("Opcional: enviar outro arquivo (CSV bruto do SIDRA, base tratada ou XLSX)", type=["csv", "xlsx"])
try:
    base = ler_upload(up) if up else base_padrao()
except Exception as e:
    st.sidebar.error(f"Não consegui ler o arquivo: {e}")
    st.stop()
if base is None:
    st.info("Coloque o arquivo tabela4709.csv na pasta dados/ ou envie-o pela barra lateral.")
    st.stop()
faltam = [c for c in OBRIGATORIAS if c not in base.columns]
if faltam:
    st.error(f"Colunas ausentes: {faltam}. Use o CSV bruto do SIDRA ou a base_tratada.csv.")
    st.stop()
base["eh_capital"] = base["eh_capital"].astype(bool)

# ------------------------------------------------------------------ Filtros
st.sidebar.header("🔎 Filtros")
metrica_nome = st.sidebar.radio("Métrica de crescimento", list(METRICAS))
M = METRICAS[metrica_nome]
regioes = st.sidebar.multiselect("Região", list(etl.REGIOES), default=list(etl.REGIOES))
ufs_disp = sorted(base[base["regiao"].isin(regioes)]["uf"].unique())
ufs = st.sidebar.multiselect("Unidade da Federação", ufs_disp, default=ufs_disp)
pmin, pmax = int(base["pop_2022"].min()), int(base["pop_2022"].max())
faixa = st.sidebar.slider("Recorte populacional (hab. em 2022)", pmin, pmax, (pmin, pmax))
so_cap = st.sidebar.checkbox("Apenas capitais", value=False)
st.sidebar.caption("Censos disponíveis: 2010 e 2022 (2010 compatibilizado com a malha de 2022).")

df = base[base["regiao"].isin(regioes) & base["uf"].isin(ufs) & base["pop_2022"].between(*faixa)]
if so_cap:
    df = df[df["eh_capital"]]
if len(df) < 5:
    st.warning("Poucos municípios com esses filtros. Amplie a seleção.")
    st.stop()

# ------------------------------------------------------------------ Estatística
s = df[M]
q1, med, q3 = s.quantile([.25, .5, .75])
iqr = q3 - q1
lim_i, lim_s = q1 - 1.5 * iqr, q3 + 1.5 * iqr
out_alto, out_baixo = df[s > lim_s], df[s < lim_i]
moda = s.round(1).mode().iloc[0]

st.title("📈 População e Crescimento Demográfico")
st.caption("Consultoria de dados para os prefeitos de Curitiba, Porto Alegre, Belo Horizonte, Salvador e "
           "Florianópolis · Fonte: IBGE, Censo Demográfico 2010 e 2022 (SIDRA, tabela 4709)")

k = st.columns(5)
k[0].metric("Municípios", n(len(df)))
k[1].metric("Média", f"{n(s.mean(), 2)}")
k[2].metric("Mediana", f"{n(med, 2)}")
k[3].metric("IQR", f"{n(iqr, 2)}")
k[4].metric("Desvio padrão", f"{n(s.std(), 2)}")
t10, t22 = df["pop_2010"].sum(), df["pop_2022"].sum()
st.write(f"População do recorte: **{n(t10)}** (2010) → **{n(t22)}** (2022): "
         f"**{n((t22 / t10 - 1) * 100, 1)}%** no período.")

tab1, tab2, tab3 = st.tabs(["📊 Estatísticas e outliers", "🏙️ BH e capitais", "📰 Notícias e imagens"])

# ------------------------------------------------------------------ Tab 1
with tab1:
    medidas = pd.DataFrame({"Medida": ["Média", "Mediana", "Moda (arred. 0,1)", "Q1", "Q3", "IQR", "Amplitude",
                                       "Desvio padrão", "Variância", "Limite inferior (Q1−1,5·IQR)",
                                       "Limite superior (Q3+1,5·IQR)"],
                            "Valor": [s.mean(), med, moda, q1, q3, iqr, s.max() - s.min(),
                                      s.std(), s.var(), lim_i, lim_s]})
    medidas["Valor"] = medidas["Valor"].map(lambda v: n(v, 2))
    a, b = st.columns([1, 2])
    with a:
        ui.tabela(medidas, hide_index=True)
    fig = px.histogram(df, x=M, nbins=70, labels={M: metrica_nome}, title="Distribuição entre os municípios")
    fig.add_vline(x=s.mean(), line_color="red", annotation_text="Média")
    fig.add_vline(x=med, line_color="green", annotation_text="Mediana", annotation_position="bottom right")
    with b:
        ui.grafico(fig)

    fig = px.box(df, x="regiao", y=M, color="regiao", points="outliers", hover_name="municipio",
                 hover_data=["uf", "pop_2022"], labels={M: metrica_nome, "regiao": "Região"},
                 title="Boxplot por região (pontos = outliers pela regra 1,5·IQR)")
    ui.grafico(fig)

    st.markdown(f"**Outliers:** {n(len(out_alto))} de crescimento muito alto (acima de {n(lim_s, 1)}) e "
                f"{n(len(out_baixo))} de queda muito acentuada (abaixo de {n(lim_i, 1)}).")
    cols = ["municipio", "uf", "pop_2010", "pop_2022", "variacao_abs", M]
    c1, c2 = st.columns(2)
    c1.markdown("🔼 **10 maiores crescimentos**")
    with c1:
        ui.tabela(df.nlargest(10, M)[cols].round(2), hide_index=True)
    c2.markdown("🔽 **10 maiores quedas**")
    with c2:
        ui.tabela(df.nsmallest(10, M)[cols].round(2), hide_index=True)
    ncai = int((df["variacao_abs"] < 0).sum())
    dif = s.mean() - med
    st.info(f"**Leitura:** {n(ncai)} municípios ({n(ncai / len(df) * 100, 1)}%) perderam população. "
            f"A média ({n(s.mean(), 2)}) fica {'acima' if dif > 0 else 'abaixo'} da mediana ({n(med, 2)}) "
            f"em {n(abs(dif), 2)}: os outliers "
            f"{'de alto crescimento puxam a média para cima' if dif > 0 else 'de queda puxam a média para baixo'}. "
            f"Para o município típico, a mediana é a referência mais robusta.")

# ------------------------------------------------------------------ Tab 2
with tab2:
    caps = base[base["eh_capital"]].copy()
    nomes_caps = sorted(caps["municipio"])
    foco = st.selectbox("Capital em destaque", nomes_caps, index=nomes_caps.index("Belo Horizonte"))
    comp = st.multiselect("Comparar com", nomes_caps, default=[c for c in etl.PERSONAS if c != foco])
    sel = caps[caps["municipio"].isin([foco] + comp)].copy()

    # posição nacional e dentro do estado (usa a base completa, sem filtros)
    sel["percentil_BR"] = [(base[M] < v).mean() * 100 for v in sel[M]]
    sel["ranking_na_UF"] = [int((base[base["uf"] == u][M] > v).sum() + 1) for u, v in zip(sel["uf"], sel[M])]
    sel["municipios_na_UF"] = [int((base["uf"] == u).sum()) for u in sel["uf"]]
    ui.tabela(sel[["municipio", "uf", "pop_2010", "pop_2022", "variacao_abs", "cresc_acum_pct",
                   "taxa_anual_calc_pct", "percentil_BR", "ranking_na_UF", "municipios_na_UF"]]
              .sort_values(M, ascending=False).round(2), hide_index=True)

    sel["destaque"] = np.where(sel["municipio"] == foco, "Em destaque", "Comparação")
    fig = px.bar(sel.sort_values(M), x=M, y="municipio", orientation="h", color="destaque",
                 color_discrete_map={"Em destaque": "#d62728", "Comparação": "#7f8c9a"},
                 labels={M: metrica_nome, "municipio": ""}, title="Capitais comparadas")
    fig.add_vline(x=base[M].median(), line_dash="dash", annotation_text="Mediana dos municípios do Brasil")
    ui.grafico(fig)

    f = sel[sel["municipio"] == foco].iloc[0]
    g1, g2 = st.columns(2)
    fig = go.Figure(go.Box(y=base[M], name="Brasil", boxpoints=False))
    fig.add_trace(go.Scatter(x=["Brasil"], y=[f[M]], mode="markers+text", text=[foco], textposition="middle right",
                             marker=dict(size=13, color="red"), name=foco))
    fig.update_layout(title="Brasil: onde a capital se posiciona", yaxis_title=metrica_nome)
    with g1:
        ui.grafico(fig)
    uf_df = base[base["uf"] == f["uf"]]
    fig = px.histogram(uf_df, x=M, nbins=40, labels={M: metrica_nome}, title=f"Municípios de {f['uf']}")
    fig.add_vline(x=f[M], line_color="red", annotation_text=foco)
    with g2:
        ui.grafico(fig)

    sinal = "perdeu" if f["variacao_abs"] < 0 else "ganhou"
    st.info(f"**{foco} ({f['uf']})** {sinal} {n(abs(f['variacao_abs']))} habitantes entre 2010 e 2022 "
            f"({n(f['cresc_acum_pct'], 2)}% no período; {n(f['taxa_anual_calc_pct'], 2)}% a.a.). "
            f"Está acima de {n(f['percentil_BR'], 1)}% dos municípios brasileiros e na posição "
            f"{int(f['ranking_na_UF'])}ª de {int(f['municipios_na_UF'])} em {f['uf']}. "
            f"Implicação para Planos Diretores: planejar saúde e infraestrutura com base na população "
            f"efetiva de 2022, não na de 2010.")

# ------------------------------------------------------------------ Tab 3
with tab3:
    st.markdown("### Reportagens e imagens do tema")
    temas = {"Transição demográfica do Brasil": "transição demográfica Brasil",
             "Envelhecimento da população brasileira": "envelhecimento população Brasil Censo 2022",
             "Capitais perdendo população": "capitais perderam população Censo 2022",
             "Expansão urbana e crescimento das cidades": "expansão urbana cidades Brasil"}
    for titulo, q in temas.items():
        st.markdown(f"- **{titulo}**: [buscar reportagens](https://news.google.com/search?q={quote(q)}&hl=pt-BR)")
    pasta = os.path.join(AQUI, "assets")
    imgs = sorted(f for f in os.listdir(pasta)) if os.path.isdir(pasta) else []
    imgs = [f for f in imgs if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    if imgs:
        cols = st.columns(min(3, len(imgs)))
        for i, f in enumerate(imgs):
            with cols[i % len(cols)]:
                ui.imagem(os.path.join(pasta, f), caption=os.path.splitext(f)[0])
    else:
        st.info("Coloque fotos na pasta `assets/` (jpg/png) para aparecerem aqui. "
                "Substitua os links de busca por 3 reportagens reais (título, veículo, data e link).")