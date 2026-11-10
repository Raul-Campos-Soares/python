import sys, types
sys.path.insert(0, "."); sys.path.insert(0, "..")
import fumaca as F
F.instalar()
exec(open("teste_mulheres.py").read().split("for modo in")[0])      # reutiliza gerar() do teste sintético
import dados_mulheres as DM
import requests

DM.fetch_sidra = lambda *a, **k: DM._api_para_raw(gerar("grupos"))
class R:
    def json(self): return {"type": "FeatureCollection", "features": []}
requests.get = lambda *a, **k: R()

ok = True
for o in [{}, {"Indicador analisado": "razao_sexo"}, {"Indicador analisado": "pct_idosas"},
          {"Indicador analisado": "idade_med_f"}, {"Indicador analisado": "Mulheres"},
          {"🗺️ Mostrar mapa coroplético por UF (baixa a malha do IBGE)": True},
          {"Região": ["Nordeste"]}]:
    e = F.rodar("p3_mulheres.py", **o)
    print(f"p3 {str(o)[:70]:70s} -> {e} gráficos={F.LOG['plots']} erros={F.LOG['error']} avisos={F.LOG['warning']}")
    ok &= e == "ok"
print("RESULTADO P3", "OK" if ok else "FALHOU")
