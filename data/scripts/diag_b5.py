import duckdb, sys
sys.stdout.reconfigure(encoding='utf-8')
con = duckdb.connect("data/sp_mvp.duckdb")
con.execute("SET enable_progress_bar=false")

print("=== Top 15 municipios SP por concluintes 2024 ===")
df = con.execute("""
    SELECT f.nome_municipio, f.id_municipio,
           SUM(total_concluintes) concluintes,
           SUM(total_matriculas)  matriculas,
           COUNT(DISTINCT id_ies) ies,
           d.populacao_total
    FROM fct_mercado_superior f
    JOIN dim_municipio d ON d.id_municipio = f.id_municipio
    WHERE f.sigla_uf = 'SP' AND f.ano = 2024
    GROUP BY 1,2,6 ORDER BY 3 DESC LIMIT 15
""").df()
print(df.to_string(index=False))

print()
print("=== Campinas: funil completo 2024 ===")
r = con.execute("""
    SELECT
        SUM(total_vagas)        vagas,
        SUM(total_inscritos)    inscritos,
        SUM(total_ingressantes) ingressantes,
        SUM(total_matriculas)   matriculas,
        SUM(total_concluintes)  concluintes,
        COUNT(DISTINCT id_ies)  ies
    FROM fct_mercado_superior
    WHERE id_municipio = '3509502' AND ano = 2024
""").fetchone()
print(f"  Vagas:         {int(r[0]):>10,}")
print(f"  Inscritos:     {int(r[1]):>10,}")
print(f"  Ingressantes:  {int(r[2]):>10,}")
print(f"  Matriculas:    {int(r[3]):>10,}")
print(f"  Concluintes:   {int(r[4]):>10,}")
print(f"  IES:           {int(r[5]):>10}")
print(f"  Conc/Mat:      {r[4]/r[3]*100:>9.1f}%")

print()
print("=== SP cidade para comparacao ===")
r2 = con.execute("""
    SELECT SUM(total_matriculas) mat, SUM(total_concluintes) conc, COUNT(DISTINCT id_ies) ies
    FROM fct_mercado_superior WHERE id_municipio = '3550308' AND ano = 2024
""").fetchone()
print(f"  SP cidade: matriculas={int(r2[0]):,} | concluintes={int(r2[1]):,} | ies={r2[2]}")

print()
print("=== Campinas vs SP cidade: conc por IES e conc/matricula ===")
print(f"  Campinas: {16867/96:.0f} conc/IES | {16867/61569*100:.1f}% conc/mat")
sp_conc = r2[1]; sp_mat = r2[0]; sp_ies = r2[2]
print(f"  SP cidade: {sp_conc/sp_ies:.0f} conc/IES | {sp_conc/sp_mat*100:.1f}% conc/mat")

con.close()
