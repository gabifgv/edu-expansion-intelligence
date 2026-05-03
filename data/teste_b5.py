import duckdb, sys
sys.stdout.reconfigure(encoding='utf-8')

con = duckdb.connect("data/sp_mvp.duckdb")
con.execute("SET enable_progress_bar=false")

# ── Escopo: SP inteiro — valida lógica para todos os municípios ───────────────
FILTRO = "sigla_uf = 'SP'"
ESCOPO = "SP inteiro"

print(f"=== BLOCO 5: Pipeline Universitário — {ESCOPO} ===\n")

# ── KPIs ──────────────────────────────────────────────────────────────────────
r = con.execute(f"""
    SELECT
        SUM(CASE WHEN ano=2024 THEN total_concluintes ELSE 0 END) c2024,
        SUM(CASE WHEN ano=2023 THEN total_concluintes ELSE 0 END) c2023,
        SUM(CASE WHEN ano=2020 THEN total_concluintes ELSE 0 END) c2020,
        COUNT(DISTINCT CASE WHEN ano=2024 THEN id_ies END) ies_2024,
        COUNT(DISTINCT CASE WHEN ano=2024 THEN id_municipio END) municipios_2024
    FROM fct_mercado_superior WHERE {FILTRO}
""").fetchone()
c2024, c2023, c2020, n_ies, n_mun = r
d23 = (c2024 - c2023) / c2023 * 100
d20 = (c2024 - c2020) / c2020 * 100
print(f"Concluintes 2024: {c2024:,.0f}  |  vs 2023: {d23:+.1f}%  |  vs 2020: {d20:+.1f}%")
print(f"IES em 2024: {n_ies:,}  |  Municípios com dados: {n_mun:,}\n")

# ── Serie temporal ────────────────────────────────────────────────────────────
print("SERIE TEMPORAL — SP inteiro")
print(f"{'Ano':<6} {'Presencial':>12} {'EaD':>10} {'Total':>10}")
print("-" * 44)
df_serie = con.execute(f"""
    SELECT ano,
        SUM(CASE WHEN modalidade_ensino='Presencial' THEN total_concluintes ELSE 0 END) pres,
        SUM(CASE WHEN modalidade_ensino='Curso a distância' THEN total_concluintes ELSE 0 END) ead,
        SUM(total_concluintes) total
    FROM fct_mercado_superior WHERE {FILTRO}
    GROUP BY ano ORDER BY ano
""").df()
for _, r in df_serie.iterrows():
    print(f"  {int(r.ano):<4} {int(r.pres):>12,} {int(r.ead):>10,} {int(r.total):>10,}")

# ── Reclassificações INEP: cursos novos em 2024 com volume alto ───────────────
print("\nRECLASSIFICAÇÕES INEP — cursos em 2024 sem histórico em 2023 (SP, >=500 conc)")
df_reclass = con.execute(f"""
    WITH base AS (
        SELECT nome_area_geral, nome_area_detalhada,
            SUM(CASE WHEN ano=2024 THEN total_concluintes ELSE 0 END) c2024,
            SUM(CASE WHEN ano=2023 THEN total_concluintes ELSE 0 END) c2023
        FROM fct_mercado_superior WHERE {FILTRO}
        GROUP BY 1, 2
    )
    SELECT nome_area_geral, nome_area_detalhada, c2024, c2023
    FROM base
    WHERE c2024 >= 500 AND c2023 = 0
    ORDER BY c2024 DESC
""").df()
print(df_reclass.to_string(index=False))

# ── Predecessores dos cursos novos ────────────────────────────────────────────
print("\nPREDECESSORES — cursos que desapareceram em 2024 na mesma área (SP)")
novas_areas = df_reclass["nome_area_geral"].unique().tolist()
for area in novas_areas:
    print(f"\n  Área: {area}")
    df_pred = con.execute(f"""
        WITH base AS (
            SELECT nome_area_detalhada,
                SUM(CASE WHEN ano=2024 THEN total_concluintes ELSE 0 END) c2024,
                SUM(CASE WHEN ano=2023 THEN total_concluintes ELSE 0 END) c2023,
                SUM(CASE WHEN ano=2020 THEN total_concluintes ELSE 0 END) c2020
            FROM fct_mercado_superior
            WHERE {FILTRO} AND nome_area_geral = '{area}'
            GROUP BY 1
        )
        SELECT nome_area_detalhada, c2023, c2020
        FROM base WHERE c2024 = 0 AND c2023 > 0
        ORDER BY c2023 DESC
    """).df()
    total_c2023 = df_pred["c2023"].sum()
    total_c2020 = df_pred["c2020"].sum()
    print(df_pred.to_string(index=False))
    print(f"  → Soma predecessoras 2023: {total_c2023:,.0f} | 2020: {total_c2020:,.0f}")
    # Delta ajustado para o novo curso nessa área
    c24_novo = df_reclass[df_reclass["nome_area_geral"]==area]["c2024"].sum()
    if total_c2023 > 0:
        d_adj = (c24_novo - total_c2023) / total_c2023 * 100
        print(f"  → Delta ajustado 2023→2024: {d_adj:+.1f}% (era 'novo' sem tratamento)")
    if total_c2020 > 0:
        d_adj20 = (c24_novo - total_c2020) / total_c2020 * 100
        print(f"  → Delta ajustado 2020→2024: {d_adj20:+.1f}%")

# ── Top 10 IES 2024 SP ────────────────────────────────────────────────────────
print("\nTOP 10 IES — SP inteiro, Concluintes 2024")
print(f"{'IES':<52} {'Rede':>8} {'Conc.':>10}")
print("-" * 76)
df_ies = con.execute(f"""
    SELECT nome_ies, rede, SUM(total_concluintes) concluintes
    FROM fct_mercado_superior WHERE {FILTRO} AND ano=2024
    GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10
""").df()
for _, r in df_ies.iterrows():
    print(f"  {str(r.nome_ies)[:52]:<52} {str(r.rede):>8} {int(r.concluintes):>10,}")

# ── Tabela area + curso SP com delta ajustado ─────────────────────────────────
print("\nTABELA — Area + Curso (SP inteiro, 2024 vs 2023, delta ajustado)")
print(f"{'Area':<38} {'Curso':<44} {'2024':>8} {'D23':>8} {'Nota'}")
print("-" * 106)

df_tab = con.execute(f"""
    WITH all_conc AS (
        SELECT nome_area_geral, nome_area_detalhada, ano,
               SUM(total_concluintes) conc
        FROM fct_mercado_superior WHERE {FILTRO}
        GROUP BY 1, 2, 3
    ),
    agg AS (
        SELECT nome_area_geral, nome_area_detalhada,
               SUM(CASE WHEN ano=2024 THEN conc ELSE 0 END) c2024,
               SUM(CASE WHEN ano=2023 THEN conc ELSE 0 END) c2023
        FROM all_conc GROUP BY 1, 2
    ),
    -- baseline por area: soma dos cursos que sumiram em 2024
    area_baseline AS (
        SELECT nome_area_geral,
               SUM(CASE WHEN c2024=0 AND c2023>0 THEN c2023 ELSE 0 END) baseline_2023
        FROM agg GROUP BY 1
    )
    SELECT p.nome_area_geral, p.nome_area_detalhada, p.c2024, p.c2023,
           ab.baseline_2023,
           CASE
               WHEN p.c2023 > 0 THEN ROUND((p.c2024-p.c2023)/p.c2023*100, 1)
               WHEN ab.baseline_2023 > 0 THEN ROUND((p.c2024-ab.baseline_2023)/ab.baseline_2023*100, 1)
               ELSE NULL
           END AS delta_adj,
           CASE WHEN p.c2023 = 0 AND ab.baseline_2023 > 0 THEN 'reclassif.' ELSE '' END AS nota
    FROM agg p
    JOIN area_baseline ab ON ab.nome_area_geral = p.nome_area_geral
    WHERE p.c2024 >= 500
    ORDER BY p.c2024 DESC
    LIMIT 20
""").df()

for _, r in df_tab.iterrows():
    d = f"{float(r.delta_adj):+.1f}%" if r.delta_adj is not None else "novo"
    print(f"  {str(r.nome_area_geral)[:38]:<38} {str(r.nome_area_detalhada)[:44]:<44} "
          f"{int(r.c2024):>8,} {d:>8}  {r.nota}")

# ── Cursos em Alta com delta ajustado ─────────────────────────────────────────
print(f"\nCURSOS EM ALTA — SP inteiro, volume >= 500, crescimento ajustado 2020→2024")
print(f"{'Area':<38} {'Curso':<44} {'2024':>8} {'Cresc':>8} {'Nota'}")
print("-" * 106)

df_alta = con.execute(f"""
    WITH all_conc AS (
        SELECT nome_area_geral, nome_area_detalhada, ano, SUM(total_concluintes) conc
        FROM fct_mercado_superior WHERE {FILTRO}
        GROUP BY 1, 2, 3
    ),
    agg2 AS (
        SELECT nome_area_geral, nome_area_detalhada,
            SUM(CASE WHEN ano=2024 THEN conc ELSE 0 END) c2024,
            SUM(CASE WHEN ano=2020 THEN conc ELSE 0 END) c2020
        FROM all_conc GROUP BY 1, 2
    ),
    area_baseline AS (
        SELECT nome_area_geral,
            SUM(CASE WHEN c2024=0 AND c2020>0 THEN c2020 ELSE 0 END) baseline_2020
        FROM agg2 GROUP BY 1
    ),
    scored AS (
        SELECT p.nome_area_geral, p.nome_area_detalhada, p.c2024,
            CASE WHEN p.c2020 > 0 THEN p.c2020 ELSE ab.baseline_2020 END AS base2020,
            CASE WHEN p.c2020 = 0 AND ab.baseline_2020 > 0 THEN 'reclassif.' ELSE '' END AS nota
        FROM agg2 p
        JOIN area_baseline ab ON ab.nome_area_geral = p.nome_area_geral
        WHERE p.c2024 >= 500
    ),
    total AS (SELECT SUM(c2024) tot FROM scored)
    SELECT s.nome_area_geral, s.nome_area_detalhada, s.c2024,
           ROUND(s.c2024/t.tot*100,1) pct,
           ROUND((s.c2024-s.base2020)/NULLIF(s.base2020,0)*100,1) cresc,
           s.nota
    FROM scored s, total t
    WHERE s.base2020 > 0 AND s.c2024 > s.base2020
    ORDER BY (s.c2024/t.tot) * ((s.c2024-s.base2020)/NULLIF(s.base2020,0)) DESC
    LIMIT 10
""").df()

for _, r in df_alta.iterrows():
    print(f"  {str(r.nome_area_geral)[:38]:<38} {str(r.nome_area_detalhada)[:44]:<44} "
          f"{int(r.c2024):>8,} {float(r.cresc):>+7.1f}%  {r.nota}")

con.close()
