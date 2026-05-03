import duckdb
import urllib.request, json

con = duckdb.connect("data/sp_mvp.duckdb")

mensalidade = 1200.0
pct_renda   = 9.0
renda_min   = mensalidade / (pct_renda / 100)

# ── Deflators IPCA (fonte: BCB série 433) ────────────────────────────────────
FALLBACK_2010 = 2.4254  # ago/2010 → mar/2026
FALLBACK_2022 = 1.1727  # dez/2022 → mar/2026

def buscar_fator(data_ini, fallback):
    try:
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial={data_ini}"
        with urllib.request.urlopen(url, timeout=10) as r:
            dados = json.loads(r.read())
        fator = 1.0
        for d in dados:
            fator *= (1 + float(d["valor"]) / 100)
        return fator, dados[-1]["data"]
    except Exception:
        return fallback, "indisponivel"

ipca_2010, ref_2010 = buscar_fator("01/08/2010", FALLBACK_2010)  # Atlas Censo 2010
ipca_2022, ref_2022 = buscar_fator("01/12/2022", FALLBACK_2022)  # RAIS 2022 (ref dez)

# ── Dados socioeconômicos (dim_municipio) ─────────────────────────────────────
cidade = con.execute("""
    SELECT nome_municipio, sigla_uf, idhm, renda_per_capita, indice_gini,
           populacao_total, populacao_urbana, taxa_superior_25_mais, prop_pobreza
    FROM dim_municipio WHERE id_municipio = '3509502'
""").df()

uf_media = con.execute("""
    SELECT
        ROUND(SUM(idhm * populacao_total) / SUM(populacao_total), 3)                 AS idhm,
        ROUND(SUM(renda_per_capita * populacao_total) / SUM(populacao_total), 2)      AS renda_per_capita,
        ROUND(SUM(indice_gini * populacao_total) / SUM(populacao_total), 3)           AS indice_gini,
        SUM(populacao_total)                                                           AS populacao_total,
        SUM(populacao_urbana)                                                          AS populacao_urbana,
        ROUND(SUM(taxa_superior_25_mais * populacao_total) / SUM(populacao_total), 2) AS taxa_superior_25_mais,
        ROUND(SUM(prop_pobreza * populacao_total) / SUM(populacao_total), 2)          AS prop_pobreza
    FROM dim_municipio WHERE sigla_uf = 'SP'
""").df()

# ── Renda média RAIS 2022 (vínculos ponderados) ───────────────────────────────
rais_c = con.execute("""
    SELECT ROUND(SUM(total_vinculos * salario_medio_reais) / SUM(total_vinculos), 2) AS renda_media_rais
    FROM fct_empregos WHERE id_municipio = '3509502' AND ano = 2022
""").fetchone()[0]

rais_sp = con.execute("""
    SELECT ROUND(SUM(total_vinculos * salario_medio_reais) / SUM(total_vinculos), 2) AS renda_media_rais
    FROM fct_empregos WHERE sigla_uf = 'SP' AND ano = 2022
""").fetchone()[0]

# ── Elegíveis / vínculos ──────────────────────────────────────────────────────
campinas_vinc = con.execute(f"""
    SELECT SUM(total_vinculos),
           SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos ELSE 0 END)
    FROM fct_empregos WHERE id_municipio = '3509502' AND ano = 2022
""").fetchone()

sp_vinc = con.execute(f"""
    SELECT SUM(total_vinculos),
           SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos ELSE 0 END)
    FROM fct_empregos WHERE sigla_uf = 'SP' AND ano = 2022
""").fetchone()

c = cidade.iloc[0].copy()
u = uf_media.iloc[0].copy()

# Aplica deflator Atlas 2010 → atual
c["renda_per_capita"] = round(float(c["renda_per_capita"]) * ipca_2010, 2)
u["renda_per_capita"] = round(float(u["renda_per_capita"]) * ipca_2010, 2)

# Aplica deflator RAIS 2022 → atual
c["renda_media_rais"] = round(rais_c  * ipca_2022, 2)
u["renda_media_rais"] = round(rais_sp * ipca_2022, 2)

pct_eleg_c  = campinas_vinc[1] / campinas_vinc[0] * 100
pct_eleg_sp = sp_vinc[1]       / sp_vinc[0]       * 100
delta_pp    = round(pct_eleg_c - pct_eleg_sp, 2)
delta_pp_str = f"+{delta_pp} pp" if delta_pp > 0 else f"{delta_pp} pp"

# ── Output ────────────────────────────────────────────────────────────────────
print(f"=== BLOCO 1: {c['nome_municipio']}/{c['sigla_uf']} vs SP (ponderado por populacao) ===")
print(f"Rendas em valores de {ref_2010} | IPCA: x{ipca_2010:.4f} (Atlas) / x{ipca_2022:.4f} (RAIS 2022)\n")

metricas = [
    ("IDHM geral",                    "idhm",              True,  False),
    ("Renda per capita (R$)",          "renda_per_capita",  True,  True),
    ("Renda media RAIS 2022 (R$)",     "renda_media_rais",  True,  True),
    ("Indice de Gini",                 "indice_gini",       False, False),
    ("Populacao total",                "populacao_total",   None,  False),
    ("Populacao urbana",               "populacao_urbana",  None,  False),
    ("Pop. 25+ c/ superior (%)",       "taxa_superior_25_mais", True, False),
    ("Prop. em pobreza (%)",           "prop_pobreza",      False, False),
]

print(f"{'Indicador':<38} {'Campinas':>12} {'Media SP':>12} {'Delta':>10}  Status")
print("-" * 86)
for label, col, maior_e_melhor, is_currency in metricas:
    cv = float(c[col]) if c[col] is not None else 0
    uv = float(u[col]) if u[col] is not None else 0
    cv_str = f"R${cv:>10,.2f}" if is_currency else f"{round(cv,2):>12}"
    uv_str = f"R${uv:>10,.2f}" if is_currency else f"{round(uv,2):>12}"
    if uv != 0 and maior_e_melhor is not None:
        delta = round((cv - uv) / abs(uv) * 100, 1)
        status = ("ACIMA" if delta > 0 else "abaixo") if maior_e_melhor else ("ACIMA" if delta < 0 else "abaixo")
        delta_str = f"+{delta}%" if delta > 0 else f"{delta}%"
    else:
        delta_str = "-"
        status = "neutro"
    print(f"{label:<38} {cv_str} {uv_str} {delta_str:>10}  {status}")

print("-" * 86)
status_eleg = "ACIMA" if delta_pp > 0 else "abaixo"
print(f"{'Elegiveis / vinculos (2022)':<38} {pct_eleg_c:>11.2f}% {pct_eleg_sp:>11.2f}% {delta_pp_str:>10}  {status_eleg}")
print(f"  (Renda minima: R${renda_min:,.0f}/mes | Mensalidade R${mensalidade:,.0f} @ {pct_renda}% renda)")

con.close()
