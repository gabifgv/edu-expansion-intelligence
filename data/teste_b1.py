import duckdb
con = duckdb.connect("data/sp_mvp.duckdb")

mensalidade = 1200.0
pct_renda   = 9.0
renda_min   = mensalidade / (pct_renda / 100)

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

campinas_vinc = con.execute(f"""
    SELECT
        SUM(total_vinculos)                                                               AS vinculos_totais,
        SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos ELSE 0 END) AS vinculos_elegiveis
    FROM fct_empregos
    WHERE id_municipio = '3509502' AND ano = 2022
""").fetchone()

sp_vinc = con.execute(f"""
    SELECT
        SUM(total_vinculos)                                                               AS vinculos_totais,
        SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos ELSE 0 END) AS vinculos_elegiveis
    FROM fct_empregos
    WHERE sigla_uf = 'SP' AND ano = 2022
""").fetchone()

c = cidade.iloc[0]
u = uf_media.iloc[0]

pct_eleg_c  = campinas_vinc[1] / campinas_vinc[0] * 100
pct_eleg_sp = sp_vinc[1]       / sp_vinc[0]       * 100
delta_pp    = round(pct_eleg_c - pct_eleg_sp, 2)
delta_pp_str = f"+{delta_pp} pp" if delta_pp > 0 else f"{delta_pp} pp"

print(f"=== BLOCO 1: {c['nome_municipio']}/{c['sigla_uf']} vs SP (ponderado por populacao) ===\n")

metricas = [
    ("IDHM geral",               "idhm",                  True,  "delta_pct"),
    ("Renda per capita (R$)",    "renda_per_capita",      True,  "delta_pct"),
    ("Indice de Gini",           "indice_gini",           False, "delta_pct"),
    ("Populacao total",          "populacao_total",       None,  None),
    ("Populacao urbana",         "populacao_urbana",      None,  None),
    ("Pop. 25+ c/ superior (%)", "taxa_superior_25_mais", True,  "delta_pct"),
    ("Prop. em pobreza (%)",     "prop_pobreza",          False, "delta_pct"),
]

print(f"{'Indicador':<35} {'Campinas':>12} {'Media SP':>12} {'Delta':>10}  Status")
print("-" * 82)
for label, col, maior_e_melhor, tipo_delta in metricas:
    cv = float(c[col]) if c[col] else 0
    uv = float(u[col]) if u[col] else 0
    if uv != 0 and maior_e_melhor is not None:
        delta = round((cv - uv) / abs(uv) * 100, 1)
        status = ("ACIMA" if delta > 0 else "abaixo") if maior_e_melhor else ("ACIMA" if delta < 0 else "abaixo")
        delta_str = f"+{delta}%" if delta > 0 else f"{delta}%"
    else:
        delta_str = "-"
        status = "neutro"
    print(f"{label:<35} {round(cv,2):>12} {round(uv,2):>12} {delta_str:>10}  {status}")

# Nova métrica: elegíveis / total vínculos (delta em pontos percentuais)
print("-" * 82)
status_eleg = "ACIMA" if delta_pp > 0 else "abaixo"
print(f"{'Elegiveis / vinculos (2022)':<35} {pct_eleg_c:>11.2f}% {pct_eleg_sp:>11.2f}% {delta_pp_str:>10}  {status_eleg}")
print(f"  (Renda minima: R${renda_min:,.0f}/mes | Mensalidade R${mensalidade:,.0f} @ {pct_renda}% renda)")

con.close()
