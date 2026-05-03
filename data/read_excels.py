import pandas as pd, sys, duckdb
sys.stdout.reconfigure(encoding='utf-8')

fgv = pd.read_excel('data/portfolio_fgv.xlsx')
conc = pd.read_excel('data/portfolio_concorrentes.xlsx')
dep = pd.read_excel('data/fgv-depara.xlsx')

print('=== FGV: 125 cursos ===')
for c in fgv['Curso'].tolist():
    print(f'  {c}')

print()
print('=== CONCORRENTES: escolas ===')
print(sorted(conc['Escola'].dropna().unique().tolist()))

print()
print('=== CONCORRENTES: categorias ===')
print(sorted(conc['Categoria de Curso'].dropna().unique().tolist()))

print()
print('=== CONCORRENTES: cursos por escola ===')
print(conc.groupby('Escola').size().sort_values(ascending=False).to_string())

print()
print('=== CONCORRENTES: cursos por categoria ===')
print(conc.groupby('Categoria de Curso').size().sort_values(ascending=False).to_string())

print()
print('=== DEPARA: CURSO_AGRUPADO_FGV unicos ===')
print(sorted(dep['CURSO_AGRUPADO_FGV'].dropna().unique().tolist()))

print()
print('=== DEPARA: escolas mapeadas ===')
print(sorted(dep['GRUPO_IES_ABR'].dropna().unique().tolist()))

print()
print('=== DEPARA: amostra CO_CURSO no DuckDB ===')
con2 = duckdb.connect('data/sp_mvp.duckdb')
con2.execute('SET enable_progress_bar=false')
for c in dep['CO_CURSO'].dropna().astype(str).head(8).tolist():
    r = con2.execute(f"SELECT COUNT(*) FROM fct_mercado_superior WHERE id_curso='{c}'").fetchone()
    print(f'  CO_CURSO {c}: {r[0]} linhas')
con2.close()
