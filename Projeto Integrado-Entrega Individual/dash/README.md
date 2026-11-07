# ♀️ Mulheres no Brasil — Números que Falam (Projeto Integrador)

Indicador: **Mulheres** (população feminina; recortes e comparações territoriais) — Censo 2022 / IBGE.

## 1) Onde está o CSV
Fonte oficial: **SIDRA, tabela 9514** — *População residente, por sexo, idade e forma de declaração da idade* (Censo 2022).
https://sidra.ibge.gov.br/tabela/9514

No SIDRA: **Território = Unidade da Federação (todas)** · **Sexo = Homens e Mulheres (e Total)** ·
**Idade = grupos de 5 anos (0 a 4 … 100 anos ou mais) e Total** · Ano = 2022 → *Download → CSV*.
Coloque o arquivo na pasta `dados/` **ou** envie pelo botão de upload na barra lateral.
Sem arquivo, o app tenta baixar a tabela direto da API do SIDRA.
(Para municípios, exporte o mesmo recorte com Território = Município; o app troca o nível automaticamente.)

## 2) Rodar
```
pip install -r requirements.txt
streamlit run app.py
```

## 3) O que o app entrega
- Upload CSV/XLSX + ETL automático (cabeçalho/rodapé do SIDRA, "-"/"X", ordem das idades)
- Filtros: ano, nível (UF/município), região, UF, faixa etária, indicador
- KPIs: total de mulheres, % de mulheres, razão de sexo, média, mediana, IQR, desvio padrão
- Gráficos: barras ranking, barras homens × mulheres, boxplot, histograma, pirâmide etária, razão de sexo por idade, mapa coroplético (opcional)
- Estatística completa (média, mediana, moda, Q1, Q3, IQR, amplitude, variância, desvio padrão, CV, outliers 1,5·IQR)
- Respostas às perguntas de negócio geradas a partir dos dados filtrados
- Notícias (links) e infográficos em `imagens/` (pode trocar pelas suas fotos .png/.jpg)

Arquivos: `app.py` (interface) · `dados.py` (ETL e estatística).
