import duckdb
import pandas as pd

con = duckdb.connect("data/sp_mvp.duckdb")

mensalidade = 1200.0
pct_renda   = 9.0
renda_min   = mensalidade / (pct_renda / 100)

print(f"=== BLOCO 2+3: Mercado de Trabalho e Tecido Empresarial - Campinas/SP ===")
print(f"Renda minima: R${renda_min:,.2f} | Empregos: 2022 | Estabs: 2024\n")

# ── TABELA 1: Por Setor ───────────────────────────────────────────────────────
df_setor = con.execute(f"""
    WITH empregos AS (
        SELECT descricao_subsetor,
               SUM(total_vinculos) AS vinculos,
               ROUND(SUM(total_vinculos * salario_medio_reais)
                     / NULLIF(SUM(total_vinculos), 0), 0)                                        AS sal_medio_total,
               SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos ELSE 0 END)  AS elegiveis,
               ROUND(
                   SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos * salario_medio_reais ELSE 0 END)
                   / NULLIF(SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos ELSE 0 END), 0)
               , 0)                                                                              AS sal_medio_eleg
        FROM fct_empregos
        WHERE id_municipio = '3509502' AND ano = 2022
        GROUP BY descricao_subsetor
    ),
    estabs AS (
        SELECT descricao_subsetor, SUM(total_estabelecimentos) AS estabs
        FROM fct_estabelecimentos
        WHERE id_municipio = '3509502' AND ano = 2024
        GROUP BY descricao_subsetor
    )
    SELECT
        e.descricao_subsetor                                          AS setor,
        COALESCE(es.estabs, 0)                                        AS estabs,
        ROUND(e.vinculos / NULLIF(es.estabs, 0), 1)                  AS func_por_empresa,
        e.vinculos,
        e.sal_medio_total,
        e.elegiveis,
        ROUND(100.0 * e.elegiveis / NULLIF(e.vinculos, 0), 1)        AS pct_eleg,
        CASE WHEN e.elegiveis >= 5 THEN e.sal_medio_eleg ELSE NULL END AS sal_medio_eleg
    FROM empregos e
    LEFT JOIN estabs es ON es.descricao_subsetor = e.descricao_subsetor
    WHERE es.estabs IS NOT NULL
    ORDER BY e.elegiveis DESC
""").df()

print("TABELA 1 — Por Setor")
print(f"{'Setor':<42} {'Estabs':>7} {'Func/emp':>8} {'Vinculos':>9} {'Sal.medio':>11} {'Eleg.':>7} {'%eleg':>6} {'Sal.eleg':>11}")
print("-" * 108)
for _, r in df_setor.iterrows():
    fe = f"{float(r['func_por_empresa']):,.0f}" if r['func_por_empresa'] and float(r['func_por_empresa']) > 0 else "-"
    sm = f"R${int(r['sal_medio_total']):,}"
    se = f"R${int(r['sal_medio_eleg']):,}" if r['sal_medio_eleg'] and r['sal_medio_eleg'] > 0 else "-"
    print(f"  {str(r['setor'])[:42]:<42} {int(r['estabs']):>7,} {fe:>8} {int(r['vinculos']):>9,} {sm:>11} {int(r['elegiveis']):>7,} {float(r['pct_eleg']):>5.1f}% {se:>11}")

# ── TABELA 2: Por Cargo ───────────────────────────────────────────────────────
df_raw = con.execute(f"""
    SELECT
        descricao_subsetor AS setor,
        descricao_cargo    AS cargo,
        SUM(total_vinculos)                                                               AS vinculos,
        SUM(total_vinculos * salario_medio_reais)                                         AS soma_sal_total,
        SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos ELSE 0 END)  AS elegiveis,
        SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos * salario_medio_reais ELSE 0 END) AS soma_sal_eleg
    FROM fct_empregos
    WHERE id_municipio = '3509502' AND ano = 2022
    GROUP BY descricao_subsetor, descricao_cargo
""").df()

df_cargo = df_raw.groupby("cargo", as_index=False).agg(
    vinculos=("vinculos", "sum"),
    soma_sal_total=("soma_sal_total", "sum"),
    elegiveis=("elegiveis", "sum"),
    soma_sal_eleg=("soma_sal_eleg", "sum"),
)
df_cargo["sal_medio_total"] = (df_cargo["soma_sal_total"] / df_cargo["vinculos"]).round(0)
df_cargo["pct_eleg"]        = (df_cargo["elegiveis"] / df_cargo["vinculos"] * 100).round(1)
df_cargo["sal_medio_eleg"]  = (df_cargo["soma_sal_eleg"] / df_cargo["elegiveis"].replace(0, float("nan"))).round(0)
df_cargo.loc[df_cargo["elegiveis"] < 5, "sal_medio_eleg"] = None
df_cargo = df_cargo[df_cargo["elegiveis"] > 0].sort_values("elegiveis", ascending=False)

setores_disponiveis = sorted(df_raw["setor"].dropna().unique().tolist())

print(f"\nTABELA 2 — Por Cargo (filtro de setor no dashboard | {len(setores_disponiveis)} setores disponíveis)")
print(f"{'Cargo':<40} {'Vinculos':>9} {'Sal.medio':>11} {'Eleg.':>7} {'%eleg':>6} {'Sal.eleg':>11}")
print("-" * 90)
for _, r in df_cargo.head(20).iterrows():
    sm = f"R${int(r['sal_medio_total']):,}"
    se = f"R${int(r['sal_medio_eleg']):,}" if r["sal_medio_eleg"] and r["sal_medio_eleg"] > 0 else "-"
    print(f"  {str(r['cargo'])[:40]:<40} {int(r['vinculos']):>9,} {sm:>11} {int(r['elegiveis']):>7,} {float(r['pct_eleg']):>5.1f}% {se:>11}")
print(f"  ... top 20 de {len(df_cargo)} cargos com elegíveis")

con.close()
