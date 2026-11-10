"""Tabelas geográficas compartilhadas pelas quatro páginas (UFs, regiões, capitais)."""
REGIOES = ["Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"]

# sigla -> (nome, região, código IBGE)
UFS = {
    "RO": ("Rondônia", "Norte", 11), "AC": ("Acre", "Norte", 12), "AM": ("Amazonas", "Norte", 13),
    "RR": ("Roraima", "Norte", 14), "PA": ("Pará", "Norte", 15), "AP": ("Amapá", "Norte", 16),
    "TO": ("Tocantins", "Norte", 17),
    "MA": ("Maranhão", "Nordeste", 21), "PI": ("Piauí", "Nordeste", 22), "CE": ("Ceará", "Nordeste", 23),
    "RN": ("Rio Grande do Norte", "Nordeste", 24), "PB": ("Paraíba", "Nordeste", 25),
    "PE": ("Pernambuco", "Nordeste", 26), "AL": ("Alagoas", "Nordeste", 27), "SE": ("Sergipe", "Nordeste", 28),
    "BA": ("Bahia", "Nordeste", 29),
    "MG": ("Minas Gerais", "Sudeste", 31), "ES": ("Espírito Santo", "Sudeste", 32),
    "RJ": ("Rio de Janeiro", "Sudeste", 33), "SP": ("São Paulo", "Sudeste", 35),
    "PR": ("Paraná", "Sul", 41), "SC": ("Santa Catarina", "Sul", 42), "RS": ("Rio Grande do Sul", "Sul", 43),
    "MS": ("Mato Grosso do Sul", "Centro-Oeste", 50), "MT": ("Mato Grosso", "Centro-Oeste", 51),
    "GO": ("Goiás", "Centro-Oeste", 52), "DF": ("Distrito Federal", "Centro-Oeste", 53),
}
UF_REGIAO = {s: v[1] for s, v in UFS.items()}

# sigla da UF -> nome da capital
CAPITAIS = {
    "RO": "Porto Velho", "AC": "Rio Branco", "AM": "Manaus", "RR": "Boa Vista", "PA": "Belém", "AP": "Macapá",
    "TO": "Palmas", "MA": "São Luís", "PI": "Teresina", "CE": "Fortaleza", "RN": "Natal", "PB": "João Pessoa",
    "PE": "Recife", "AL": "Maceió", "SE": "Aracaju", "BA": "Salvador", "MG": "Belo Horizonte",
    "ES": "Vitória", "RJ": "Rio de Janeiro", "SP": "São Paulo", "PR": "Curitiba", "SC": "Florianópolis",
    "RS": "Porto Alegre", "MS": "Campo Grande", "MT": "Cuiabá", "GO": "Goiânia", "DF": "Brasília",
}
