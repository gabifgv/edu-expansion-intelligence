"""Diagnóstico: por que filtro Indústria Química não traz cargos em Santos?"""
import duckdb, sys
sys.stdout.reconfigure(encoding='utf-8')

con = duckdb.connect("data/sp_mvp.duckdb")
con.execute("SET enable_progress_bar=false")

# Santos id_municipio
santos = con.execute("SELECT id_municipio, nome_municipio FROM dim_municipio WHERE nome_municipio = 'Santos' AND sigla_uf='SP'").fetchall()
print(f"Santos: {santos}")

renda_min = 4000
ano = 2024

print("\n=== Setores em Santos com cargos (lista única) ===")
df = con.execute(f"""
    SELECT descricao_subsetor AS setor,
           SUM(total_vinculos) AS vinculos,
           SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos ELSE 0 END) AS eleg,
           COUNT(DISTINCT descricao_cargo) AS n_cargos
    FROM fct_empregos
    WHERE id_municipio = '3548500' AND ano = {ano}
      AND descricao_cargo IS NOT NULL AND descricao_subsetor IS NOT NULL
    GROUP BY 1
    ORDER BY 2 DESC
""").df()
print(df.to_string(index=False))

print("\n=== Indústria Química em Santos: tem dados? ===")
df2 = con.execute(f"""
    SELECT descricao_cargo,
           SUM(total_vinculos) v,
           SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos ELSE 0 END) e
    FROM fct_empregos
    WHERE id_municipio = '3548500' AND ano = {ano}
      AND descricao_subsetor = 'Indústria Química'
    GROUP BY 1
    ORDER BY 2 DESC LIMIT 10
""").df()
print(df2.to_string(index=False))
print(f"Total cargos Indústria Química Santos: {len(df2)} | Total elegíveis: {df2['e'].sum()}")

con.close()
