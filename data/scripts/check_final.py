"""Validação final antes de construir o index.html consolidado."""
import duckdb, sys
sys.stdout.reconfigure(encoding='utf-8')

con = duckdb.connect("data/sp_mvp.duckdb")
con.execute("SET enable_progress_bar=false")

print("=== COBERTURA SP ===")
n_dim = con.execute("SELECT COUNT(*) FROM dim_municipio WHERE sigla_uf = 'SP'").fetchone()[0]
print(f"dim_municipio: {n_dim}")

anos_emp = [r[0] for r in con.execute("SELECT DISTINCT ano FROM fct_empregos ORDER BY ano").fetchall()]
print(f"fct_empregos anos: {anos_emp}")

anos_sup = [r[0] for r in con.execute("SELECT DISTINCT ano FROM fct_mercado_superior ORDER BY ano").fetchall()]
print(f"fct_mercado_superior anos: {anos_sup}")

anos_est = [r[0] for r in con.execute("SELECT DISTINCT ano FROM fct_estabelecimentos ORDER BY ano").fetchall()]
print(f"fct_estabelecimentos anos: {anos_est}")

print("\n=== AMOSTRA DE 10 CIDADES SP ===")
df = con.execute("""
    SELECT id_municipio, nome_municipio, populacao_total, idhm
    FROM dim_municipio WHERE sigla_uf = 'SP'
    ORDER BY populacao_total DESC LIMIT 10
""").df()
print(df.to_string(index=False))

print("\n=== TABELAS NO DUCKDB ===")
print(con.execute("SHOW TABLES").df().to_string(index=False))

print("\n=== VERIFICA DIM_CEP_COORDS ===")
try:
    n = con.execute("SELECT COUNT(*) FROM dim_cep_coords").fetchone()[0]
    print(f"dim_cep_coords: {n:,} CEPs")
except Exception as e:
    print(f"NAO EXISTE: {e}")

con.close()
