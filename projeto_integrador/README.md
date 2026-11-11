# Números que Falam — Descobrindo o Brasil
Painel Streamlit integrado (4 indicadores demográficos do IBGE) · Projeto Integrador · Python e Matemática

## Como rodar
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
python baixar_dados_mulheres.py  # 1 vez, precisa de internet (gera dados/censo2022_sexo_idade_uf.csv)
streamlit run app.py
```
O `baixar_dados_mulheres.py` é opcional: sem ele a página "Mulheres" baixa a tabela 9514 direto da API do IBGE
na primeira abertura (precisa de internet). As outras três páginas usam os arquivos que já estão em `dados/`.

## Estrutura
| Arquivo | O que é |
|---|---|
| `app.py` | Entrada do painel: menu de navegação (`st.navigation`) |
| `paginas/inicio.py` | Página inicial, integrantes (edite `config.py`), fontes e guia das medidas |
| `paginas/p1_populacao_idade.py` | População por idade e sexo (Projeções IBGE 2024) |
| `paginas/p2_alfabetizacao.py` | Alfabetização por sexo, UF e ano (Censo 2010/2022) |
| `paginas/p3_mulheres.py` | Mulheres no Brasil (Censo 2022, tabela 9514) |
| `paginas/p4_crescimento.py` | Crescimento demográfico 2010×2022, BH e capitais (tabela 4709) |
| `etl_crescimento.py`, `etl_alfabetizacao.py`, `dados_mulheres.py` | Leitura e tratamento de cada base |
| `estatistica.py` | Média, mediana, moda, quartis, IQR, desvio padrão, outliers (regra 1,5·IQR) |
| `geo.py`, `ui.py`, `config.py` | UFs/regiões/capitais, utilidades de interface, nomes do grupo |
| `dados/` | Bases do IBGE |
| `testes/` | Testes automáticos dos cálculos (ver abaixo) |

## O que foi alterado nos arquivos originais
- **Os quatro `app.py` viraram páginas** de um único painel: removido `st.set_page_config` (fica só no `app.py`).
- **Havia dois `etl.py` diferentes** (crescimento e alfabetização): agora são `etl_crescimento.py` e `etl_alfabetizacao.py`.
- **Módulos que faltavam foram criados:** `etl_*`, `estatistica.py`, `dados_mulheres.py`.
- **Página 1** era só um gráfico Matplotlib; foi refeita com filtros, cards (média, mediana, moda, Q1, Q3, IQR, desvio padrão),
  pirâmide etária, comparação entre as 27 UFs (ranking, boxplot, outliers), evolução 2000–2070 e texto de leitura.
- **Página 3:** a base agora é lida só de `dados/censo2022_sexo_idade*.csv` (antes pegava qualquer CSV da pasta, o que
  quebraria com as outras bases); o gráfico de evolução usava apenas o ano selecionado e passou a usar todos os anos;
  o eixo da pirâmide se ajusta aos dados.
- **Página 4:** o boxplot "onde a capital se posiciona" foi refeito com `graph_objects` para o ponto da capital cair sobre a caixa.
- Todas as chamadas `use_container_width`/`width="stretch"` passam por `ui.py`, que funciona em versões antigas e novas do Streamlit.

## Convenções estatísticas
- Quartis: interpolação linear (padrão do Pandas/NumPy). Outlier: fora de [Q1 − 1,5·IQR ; Q3 + 1,5·IQR].
- Desvio padrão/variância **amostrais (n−1)** nas séries de UFs e municípios; **populacionais (n)** na distribuição de idade da
  página 1 (dados agrupados por idade simples, onde a população é a frequência).
- Taxa anual de crescimento da página 4: `(pop2022/pop2010)^(1/12) − 1`; confere com a taxa publicada pelo IBGE (diferença máx. 0,005 p.p., arredondamento).


## Testes
`cd testes && python teste_mulheres.py && python rodar_fumaca.py && python rodar_fumaca_p3.py`
Usam Streamlit/Plotly simulados e, para a página Mulheres, dados **sintéticos** (só para testar o código, não são dados do IBGE).
