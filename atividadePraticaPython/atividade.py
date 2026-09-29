import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt
# parte 1 da atividade

df = pd.read_csv('transacoes.csv', encoding= 'latin1')

# print(df.head())
# print(df.info())
# print ("o numero de NaN q tem : " , df['valor'].isna().sum())

df['valor'] = df['valor'].fillna(
    df.groupby('estado_cliente')['valor'].transform('median')
)

# print(" o valor de NaN depois da imputação é de :", df['valor'].isna().sum())

df['plataforma'] = 'mobile'
# print(df.head())

#  parte 2 da atividade

df['data_transacao'] = pd.to_datetime(df['data_transacao']).astype('datetime64[ns]')

df['data_transacao'] = df['data_transacao'].dt.tz_localize('America/Sao_Paulo')

df['dia_semana'] = df['data_transacao'].dt.day_name()

df['mes'] = df['data_transacao'].dt.month

# print ("total de linhas antes ", len(df))
df = df.drop_duplicates  (keep= 'first')
# print("total de linha agr removendo as duplicadas", len(df))

# ver se prestou

# print(df.dtypes)
# print (df[['data_transacao', 'dia_semana', 'mes']].head())

# parte 3 da atividade 

condicao_mes = (df['mes'] == 9)
condicao_estado = (df['estado_cliente'] == 'SP') | (df['estado_cliente'] == 'RJ')
condicao_valor = (df['valor'] > 5000)

df_filtro = df[condicao_mes & condicao_estado & condicao_valor]

# os print pra testar

# print("uantidade de transacoes ", len(df_filtro) )
# print(df_filtro[['data_transacao', 'estado_cliente', 'valor']].head())

risco_dict = {
    'C100' : 'Baixo',
    'C101' : 'Alto',
    'C102' : 'Medio',
    'C103' : 'Alto',
    'C104' : 'Baixo',
    'C105' : 'Medio'
}

df['nivel_risco'] = df['id_cliente'].map(risco_dict)

tabela = df.pivot_table(
    index = 'mes',
    columns = 'nivel_risco',
    values = 'valor',
    aggfunc = 'sum',
    margins = True,
    margins_name = 'Total'
)

# print(tabela)
# print(df['valor'].sum())

# parte 4 

agrupar = df.groupby('estado_cliente')['valor']

df['zscore'] = (df['valor'] - agrupar.transform('mean')) / agrupar.transform('std')

df_anomalia = df[df['zscore'] > 2.5]

# print("anomalias achadas ", len(df_anomalia))
# print(df_anomalia[['id_cliente', 'estado_cliente', 'valor', 'zscore']].head())



#parte 5


tDia = df.set_index ('data_transacao')['valor'].resample('D').sum()


mMovel = tDia.rolling(7).mean()



fig, ax = plt.subplots(figsize=(12,6))
ax.plot(tDia.index, tDia.values, label = 'total por dia')
ax.plot(mMovel.index, mMovel.values, label = 'media movel de 7 dias',linewidth= 2  )

ax.set_ylim(bottom=0)
ax.set_title('valor total por diia')
ax.set_xlabel('data')
ax.set_ylabel('valor total')
ax.legend()

fig.autofmt_xdate()
plt.show()