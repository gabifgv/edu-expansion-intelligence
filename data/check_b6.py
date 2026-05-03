import duckdb, sys
sys.stdout.reconfigure(encoding='utf-8')
con = duckdb.connect("data/sp_mvp.duckdb")
con.execute("SET enable_progress_bar=false")

r = con.execute("""
    SELECT
        COUNT(DISTINCT d.id_municipio) mun_dim,
        COUNT(DISTINCT e.id_municipio) mun_empregos,
        COUNT(DISTINCT m.id_municipio) mun_superior,
        COUNT(DISTINCT emp.id_municipio) mun_empresas
    FROM dim_municipio d
    LEFT JOIN fct_empregos e ON e.id_municipio = d.id_municipio
    LEFT JOIN fct_mercado_superior m ON m.id_municipio = d.id_municipio AND m.ano = 2024
    LEFT JOIN fct_empresas emp ON emp.id_municipio = d.id_municipio
    WHERE d.sigla_uf = 'SP'
""").fetchone()
print(f"dim_municipio SP:          {r[0]}")
print(f"fct_empregos (algum ano):  {r[1]}")
print(f"fct_mercado_superior 2024: {r[2]}")
print(f"fct_empresas:              {r[3]}")

print("\n--- dim_municipio ---")
print(con.execute("DESCRIBE dim_municipio").df()[["column_name","column_type"]].to_string(index=False))
print("\n--- fct_empregos ---")
print(con.execute("DESCRIBE fct_empregos").df()[["column_name","column_type"]].to_string(index=False))
print("\n--- fct_mercado_superior ---")
print(con.execute("DESCRIBE fct_mercado_superior").df()[["column_name","column_type"]].to_string(index=False))
print("\n--- fct_empresas ---")
print(con.execute("DESCRIBE fct_empresas").df()[["column_name","column_type"]].to_string(index=False))

con.close()
