import duckdb, sys
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

con = duckdb.connect("data/sp_mvp.duckdb")
con.execute("SET enable_progress_bar=false")

# ── Pesos default (usuário pode ajustar no dashboard) ─────────────────────────
W1 = 0.35  # D1 Capacidade de Pagamento
W2 = 0.30  # D2 Tamanho Mercado
W3 = 0.20  # D3 Pipeline Acadêmico
W4 = 0.15  # D4 Dinamismo Econômico

print(f"=== BLOCO 6: Score de Atratividade — SP inteiro (645 municípios) ===")
print(f"Pesos: D1={W1:.0%} | D2={W2:.0%} | D3={W3:.0%} | D4={W4:.0%}\n")

# ── Ano mais recente disponível em fct_empregos ──────────────────────────────
ano_max = con.execute("SELECT MAX(ano) FROM fct_empregos").fetchone()[0]
print(f"Ano referência fct_empregos: {ano_max}")

# ── D1: Capacidade de Pagamento ───────────────────────────────────────────────
# Sub-indicadores:
#   d1a = salário médio ponderado por vínculos (proxy: pode pagar mensalidade)
#   d1b = % vínculos com salário >= 3 SM (R$3.960 ≈ teto MBA ~R$800/mês)
df_d1 = con.execute(f"""
    SELECT
        e.id_municipio,
        SUM(e.total_vinculos * e.salario_medio_reais) / NULLIF(SUM(e.total_vinculos), 0) AS avg_sal,
        SUM(CASE WHEN e.salario_medio_sm >= 3 THEN e.total_vinculos ELSE 0 END) * 1.0
            / NULLIF(SUM(e.total_vinculos), 0) AS pct_3sm
    FROM fct_empregos e
    JOIN dim_municipio d ON d.id_municipio = e.id_municipio
    WHERE d.sigla_uf = 'SP' AND e.ano = {ano_max}
    GROUP BY 1
""").df()

# ── D2: Tamanho Mercado ───────────────────────────────────────────────────────
# Sub-indicadores:
#   d2a = total vínculos formais (escala do mercado de trabalho)
#   d2b = empresas capital > R$1M por 1.000 vínculos (densidade empresarial qualificada)
df_d2 = con.execute(f"""
    WITH emp AS (
        SELECT id_municipio, SUM(total_vinculos) AS vinculos
        FROM fct_empregos
        WHERE ano = {ano_max}
        GROUP BY 1
    ),
    empres AS (
        SELECT e.id_municipio, COUNT(DISTINCT cnpj) AS n_grandes
        FROM fct_empresas e
        WHERE e.porte = '5' AND e.capital_social >= 1000000
        GROUP BY 1
    )
    SELECT d.id_municipio,
           COALESCE(v.vinculos, 0)   AS vinculos,
           COALESCE(g.n_grandes, 0) * 1000.0 / NULLIF(COALESCE(v.vinculos, 0), 0) AS grandes_per_1k
    FROM dim_municipio d
    LEFT JOIN emp v ON v.id_municipio = d.id_municipio
    LEFT JOIN empres g ON g.id_municipio = d.id_municipio
    WHERE d.sigla_uf = 'SP'
""").df()

# ── D3: Pipeline Acadêmico ────────────────────────────────────────────────────
# Sub-indicadores:
#   d3a = taxa_superior_25_mais (% pop 25+ com ensino superior — mercado pós)
#   d3b = concluintes em Negócios + TIC + Engenharia por 1.000 hab (supply pipeline)
df_d3 = con.execute("""
    WITH conc AS (
        SELECT id_municipio,
               SUM(CASE WHEN nome_area_geral IN (
                   'Negócios, administração e direito',
                   'Tecnologias da informação e comunicação',
                   'Engenharia, produção e construção'
               ) THEN total_concluintes ELSE 0 END) AS conc_alvo
        FROM fct_mercado_superior
        WHERE sigla_uf = 'SP' AND ano = 2024
        GROUP BY 1
    )
    SELECT d.id_municipio,
           COALESCE(d.taxa_superior_25_mais, 0) AS taxa_superior,
           COALESCE(c.conc_alvo, 0) * 1000.0 / NULLIF(d.populacao_total, 0) AS conc_per_1k
    FROM dim_municipio d
    LEFT JOIN conc c ON c.id_municipio = d.id_municipio
    WHERE d.sigla_uf = 'SP'
""").df()

# ── D4: Dinamismo Econômico ───────────────────────────────────────────────────
# Sub-indicadores:
#   d4a = IDHM (desenvolvimento humano)
#   d4b = crescimento vínculos ano_max vs 2020 (dinamismo recente do mercado)
df_d4 = con.execute(f"""
    WITH v_atual AS (
        SELECT id_municipio, SUM(total_vinculos) AS v_atual
        FROM fct_empregos WHERE ano = {ano_max} GROUP BY 1
    ),
    v_2020 AS (
        SELECT id_municipio, SUM(total_vinculos) AS v_2020
        FROM fct_empregos WHERE ano = 2020 GROUP BY 1
    )
    SELECT d.id_municipio,
           COALESCE(d.idhm, 0) AS idhm,
           CASE WHEN v0.v_2020 > 0
                THEN (COALESCE(va.v_atual, 0) - v0.v_2020) * 1.0 / v0.v_2020
                ELSE NULL END AS crescimento_vinculos
    FROM dim_municipio d
    LEFT JOIN v_atual va ON va.id_municipio = d.id_municipio
    LEFT JOIN v_2020 v0 ON v0.id_municipio = d.id_municipio
    WHERE d.sigla_uf = 'SP'
""").df()

# ── Base: todos os municípios SP ──────────────────────────────────────────────
df_base = con.execute("""
    SELECT id_municipio, nome_municipio, populacao_total
    FROM dim_municipio WHERE sigla_uf = 'SP'
""").df()

con.close()

# ── Merge e normalização min-max ──────────────────────────────────────────────
df = df_base.merge(df_d1, on="id_municipio", how="left") \
            .merge(df_d2, on="id_municipio", how="left") \
            .merge(df_d3, on="id_municipio", how="left") \
            .merge(df_d4, on="id_municipio", how="left")

# Preenche NaN com 0 antes de normalizar
cols_raw = ["avg_sal", "pct_3sm", "vinculos", "grandes_per_1k",
            "taxa_superior", "conc_per_1k", "idhm", "crescimento_vinculos"]
df[cols_raw] = df[cols_raw].fillna(0)

def norm(s):
    mn, mx = s.min(), s.max()
    return (s - mn) / (mx - mn + 1e-10)

df["d1a"] = norm(df["avg_sal"])
df["d1b"] = norm(df["pct_3sm"])
df["d2a"] = norm(df["vinculos"])
df["d2b"] = norm(df["grandes_per_1k"])
df["d3a"] = norm(df["taxa_superior"])
df["d3b"] = norm(df["conc_per_1k"])
df["d4a"] = norm(df["idhm"])
df["d4b"] = norm(df["crescimento_vinculos"])

df["D1"] = (df["d1a"] + df["d1b"]) / 2
df["D2"] = (df["d2a"] + df["d2b"]) / 2
df["D3"] = (df["d3a"] + df["d3b"]) / 2
df["D4"] = (df["d4a"] + df["d4b"]) / 2

df["score"] = (W1 * df["D1"] + W2 * df["D2"] + W3 * df["D3"] + W4 * df["D4"]) * 100

df = df.sort_values("score", ascending=False).reset_index(drop=True)
df["rank"] = df.index + 1

# ── Motivo: dimensão mais forte + mais fraca ──────────────────────────────────
DIM_LABELS = {
    "D1": "Cap.Pagamento",
    "D2": "Tam.Mercado",
    "D3": "Pipeline",
    "D4": "Dinamismo"
}

def motivo(row):
    scores = {k: row[k] for k in ["D1", "D2", "D3", "D4"]}
    melhor = max(scores, key=scores.get)
    pior   = min(scores, key=scores.get)
    if row["rank"] <= 50:
        return f"Força: {DIM_LABELS[melhor]} ({scores[melhor]*100:.0f})"
    else:
        return f"↑{DIM_LABELS[melhor]} ({scores[melhor]*100:.0f}) ↓{DIM_LABELS[pior]} ({scores[pior]*100:.0f})"

df["motivo"] = df.apply(motivo, axis=1)

# ── Output: top 30 + bottom 10 ────────────────────────────────────────────────
print(f"\nRANKING COMPLETO — Top 30 (de 645 municípios SP)")
print(f"{'Rank':>4} {'Município':<30} {'Score':>6} {'D1':>5} {'D2':>5} {'D3':>5} {'D4':>5}  Motivo")
print("-" * 108)

for _, r in df.head(30).iterrows():
    print(f"  {int(r['rank']):>3}. {str(r['nome_municipio'])[:30]:<30} "
          f"{r['score']:>5.1f}  "
          f"{r['D1']*100:>4.0f}  {r['D2']*100:>4.0f}  {r['D3']*100:>4.0f}  {r['D4']*100:>4.0f}  "
          f"{r['motivo']}")

print(f"\n... ({len(df)-40} municípios omitidos) ...\n")
print(f"ÚLTIMOS 10 (menores scores)")
print(f"{'Rank':>4} {'Município':<30} {'Score':>6} {'D1':>5} {'D2':>5} {'D3':>5} {'D4':>5}  Motivo")
print("-" * 108)
for _, r in df.tail(10).iterrows():
    print(f"  {int(r['rank']):>3}. {str(r['nome_municipio'])[:30]:<30} "
          f"{r['score']:>5.1f}  "
          f"{r['D1']*100:>4.0f}  {r['D2']*100:>4.0f}  {r['D3']*100:>4.0f}  {r['D4']*100:>4.0f}  "
          f"{r['motivo']}")

# ── Stats gerais ──────────────────────────────────────────────────────────────
print(f"\n=== ESTATÍSTICAS ===")
print(f"Score médio SP: {df['score'].mean():.1f}  |  Mediana: {df['score'].median():.1f}")
print(f"Maior score: {df.iloc[0]['nome_municipio']} ({df.iloc[0]['score']:.1f})")
print(f"Menor score: {df.iloc[-1]['nome_municipio']} ({df.iloc[-1]['score']:.1f})")

# Campinas
camp = df[df["id_municipio"] == "3509502"].iloc[0]
print(f"\nCampinas: rank {int(camp['rank'])}/645 | score {camp['score']:.1f}"
      f" | D1={camp['D1']*100:.0f} D2={camp['D2']*100:.0f} D3={camp['D3']*100:.0f} D4={camp['D4']*100:.0f}")
