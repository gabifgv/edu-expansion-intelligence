import duckdb, sys
sys.stdout.reconfigure(encoding='utf-8')
con = duckdb.connect("data/sp_mvp.duckdb")
con.execute("SET enable_progress_bar=false")

df = con.execute("""
    SELECT DISTINCT e.cnae_classe, em.descricao_subsetor
    FROM fct_empresas e
    JOIN fct_empregos em ON em.cnae_classe = e.cnae_classe
    WHERE e.id_municipio = '3509502'
    LIMIT 20
""").df()
print(f"{len(df)} exemplos:")
print(df.to_string(index=False))
print()

r2 = con.execute("""
    SELECT
        COUNT(DISTINCT e.cnae_classe) total,
        COUNT(DISTINCT CASE WHEN em.cnae_classe IS NOT NULL THEN e.cnae_classe END) com_match
    FROM fct_empresas e
    LEFT JOIN fct_empregos em ON em.cnae_classe = e.cnae_classe
    WHERE e.id_municipio = '3509502' AND e.porte = '5'
""").fetchone()
print(f"cnae distintos porte=5 Campinas: {r2[0]}  |  com match setor: {r2[1]}")

r3 = con.execute("""
    SELECT COUNT(*) FROM fct_empresas e
    LEFT JOIN (
        SELECT DISTINCT cnae_classe, descricao_subsetor FROM fct_empregos
    ) em ON em.cnae_classe = e.cnae_classe
    WHERE e.id_municipio = '3509502' AND e.porte = '5'
      AND em.cnae_classe IS NULL
""").fetchone()
print(f"empresas porte=5 SEM match de setor: {r3[0]:,}")

con.close()
