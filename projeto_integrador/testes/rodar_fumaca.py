import sys
sys.path.insert(0, ".")
import fumaca as F
F.instalar()
import types

def rel(pag, **o):
    e = F.rodar(pag, **o)
    print(f"{pag:26s} {str(o)[:60]:60s} -> {e:4s} gráficos={F.LOG['plots']:2d} erros={F.LOG['error']} avisos={F.LOG['warning']}")
    return e

ok = True
for pag, cfgs in {
    "p1_populacao_idade.py": [{}, {"Território": "Minas Gerais", "Sexo": "Mulheres", "Ano": 2050},
                              {"Território": "Sul", "Ano": 2000}, {"Indicador": "Razão de dependência"}],
    "p2_alfabetizacao.py": [{}, {"Ano": 2010}],
    "p4_crescimento.py": [{}, {"Métrica": "Taxa média anual (% a.a.)"}, {"Apenas capitais": True},
                          {"Capital em destaque": "Salvador"}],
}.items():
    for c in cfgs:
        ok &= rel(pag, **c) == "ok"
print("RESULTADO", "OK" if ok else "FALHOU")
