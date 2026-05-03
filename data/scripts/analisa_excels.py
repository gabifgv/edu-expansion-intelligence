import pandas as pd, sys, duckdb
sys.stdout.reconfigure(encoding='utf-8')

conc = pd.read_excel('data/portfolio_concorrentes.xlsx')
dep  = pd.read_excel('data/fgv-depara.xlsx')

# Competidores locais em Campinas
print("=== COMPETIDORES COM PRESENÇA EM CAMPINAS ===")
campinas = conc[conc['Escola'].str.contains('Campinas', case=False, na=False)]
print(f"Mackenzie Campinas: {len(campinas)} cursos")
print(campinas[['Curso','Categoria de Curso','Modalidade']].to_string(index=False))

print()
print("=== CATEGORIAS mais contestadas (todos os competidores) ===")
cat = conc.groupby('Categoria de Curso').size().sort_values(ascending=False)
print(cat.to_string())

print()
print("=== TOP ESCOLAS POR CATEGORIA ===")
top = conc.groupby(['Categoria de Curso','Escola']).size().reset_index(name='n')
top = top.sort_values(['Categoria de Curso','n'], ascending=[True, False])
for cat_name in top['Categoria de Curso'].unique():
    sub = top[top['Categoria de Curso']==cat_name].head(4)
    escolas = ', '.join(f"{r['Escola']}({r['n']})" for _, r in sub.iterrows())
    print(f"  {cat_name:<32} → {escolas}")

print()
print("=== FGV no benchmark de concorrentes ===")
fgv_conc = conc[conc['Escola']=='FGV']
print(f"FGV tem {len(fgv_conc)} cursos na base de concorrentes")
print(fgv_conc.groupby('Categoria de Curso').size().sort_values(ascending=False).to_string())

print()
print("=== DEPARA: IES em SP (CO_UF=35) ===")
sp = dep[dep['CO_UF']==35]
print(sp.groupby('GRUPO_IES_ABR').size().sort_values(ascending=False).to_string())
print()
print("=== DEPARA: UNICAMP aparece? ===")
print(dep[dep['GRUPO_IES_ABR'].str.contains('UNICAMP', case=False, na=False)])

print()
print("=== IES em Campinas no DuckDB (fct_mercado_superior 2024) ===")
con2 = duckdb.connect('data/sp_mvp.duckdb')
con2.execute('SET enable_progress_bar=false')
ies = con2.execute("""
    SELECT nome_ies, rede, SUM(total_concluintes) conc
    FROM fct_mercado_superior
    WHERE id_municipio = '3509502' AND ano = 2024
    GROUP BY 1,2 ORDER BY 3 DESC LIMIT 15
""").df()
print(ies.to_string(index=False))
con2.close()
