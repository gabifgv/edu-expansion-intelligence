"""Análise ad hoc: público elegível MBA em Campinas (parcela R$ 1.316,92, máx 9,5% renda)."""
from google.cloud import bigquery
import pandas as pd

PROJECT      = 'project-a8f8452a-3033-4dd8-99a'
ID_MUNICIPIO = '3509007'
SIGLA_UF     = 'SP'
PARCELA      = 1316.92
PCT_RENDA    = 9.5
RENDA_MIN    = round(PARCELA / (PCT_RENDA / 100), 2)

print('='*80)
print(f'ANÁLISE ELEGIBILIDADE MBA — CAMPINAS/SP')
print(f'Parcela: R$ {PARCELA:,.2f} | % renda máx: {PCT_RENDA}% | Renda mínima: R$ {RENDA_MIN:,.2f}')
print('='*80)

client = bigquery.Client(project=PROJECT)
def q(sql): return client.query(sql).to_dataframe()

# 1. Visão geral — vínculos totais vs elegíveis (2020-2022)
print('\n[1] EVOLUÇÃO DO PÚBLICO ELEGÍVEL (RAIS 2020-2022)')
print('-'*80)
df1 = q(f"""
SELECT ano,
  SUM(total_vinculos) AS total_vinculos,
  SUM(IF(salario_medio_reais >= {RENDA_MIN}, total_vinculos, 0)) AS elegiveis,
  ROUND(SAFE_DIVIDE(SUM(IF(salario_medio_reais >= {RENDA_MIN}, total_vinculos, 0)),
                    SUM(total_vinculos)) * 100, 2) AS pct_elegivel
FROM `{PROJECT}.raw_facts.fct_empregos`
WHERE id_municipio = '{ID_MUNICIPIO}' AND ano BETWEEN 2020 AND 2022
GROUP BY ano ORDER BY ano
""")
print(df1.to_string(index=False))

# 2. Comparativo Campinas vs SP vs BR (2022)
print('\n[2] CAMPINAS vs SP vs BR — VÍNCULOS ELEGÍVEIS (2022)')
print('-'*80)
df2 = q(f"""
SELECT 'Campinas' AS escopo,
  SUM(total_vinculos) AS total_vinculos,
  SUM(IF(salario_medio_reais >= {RENDA_MIN}, total_vinculos, 0)) AS elegiveis,
  ROUND(SAFE_DIVIDE(SUM(IF(salario_medio_reais >= {RENDA_MIN}, total_vinculos, 0)),
                    SUM(total_vinculos)) * 100, 2) AS pct_elegivel
FROM `{PROJECT}.raw_facts.fct_empregos`
WHERE id_municipio = '{ID_MUNICIPIO}' AND ano = 2022
UNION ALL
SELECT 'Estado SP',
  SUM(total_vinculos),
  SUM(IF(salario_medio_reais >= {RENDA_MIN}, total_vinculos, 0)),
  ROUND(SAFE_DIVIDE(SUM(IF(salario_medio_reais >= {RENDA_MIN}, total_vinculos, 0)),
                    SUM(total_vinculos)) * 100, 2)
FROM `{PROJECT}.raw_facts.fct_empregos`
WHERE sigla_uf = 'SP' AND ano = 2022
UNION ALL
SELECT 'Brasil',
  SUM(total_vinculos),
  SUM(IF(salario_medio_reais >= {RENDA_MIN}, total_vinculos, 0)),
  ROUND(SAFE_DIVIDE(SUM(IF(salario_medio_reais >= {RENDA_MIN}, total_vinculos, 0)),
                    SUM(total_vinculos)) * 100, 2)
FROM `{PROJECT}.raw_facts.fct_empregos`
WHERE ano = 2022
""")
print(df2.to_string(index=False))

# 3. Top setores com público elegível (2022) + crescimento
print('\n[3] TOP 15 SETORES POR VÍNCULOS ELEGÍVEIS (2022) + Δ% 2020→2022')
print('-'*80)
df3 = q(f"""
WITH base AS (
  SELECT ano, descricao_subsetor,
    SUM(IF(salario_medio_reais >= {RENDA_MIN}, total_vinculos, 0)) AS elegiveis,
    SUM(total_vinculos) AS total_vinc,
    ROUND(SAFE_DIVIDE(SUM(total_vinculos*salario_medio_reais), SUM(total_vinculos)),2) AS sal_med
  FROM `{PROJECT}.raw_facts.fct_empregos`
  WHERE id_municipio = '{ID_MUNICIPIO}' AND ano IN (2020, 2022)
  GROUP BY ano, descricao_subsetor
)
SELECT
  descricao_subsetor,
  MAX(IF(ano=2020, elegiveis, NULL))  AS eleg_2020,
  MAX(IF(ano=2022, elegiveis, NULL))  AS eleg_2022,
  MAX(IF(ano=2022, total_vinc, NULL)) AS total_2022,
  MAX(IF(ano=2022, sal_med, NULL))    AS salario_medio,
  ROUND(SAFE_DIVIDE(MAX(IF(ano=2022, elegiveis, NULL)),
                    NULLIF(MAX(IF(ano=2022, total_vinc, NULL)),0)) * 100, 1) AS pct_elegivel,
  ROUND(SAFE_DIVIDE(
    MAX(IF(ano=2022, elegiveis, NULL)) - MAX(IF(ano=2020, elegiveis, NULL)),
    NULLIF(MAX(IF(ano=2020, elegiveis, NULL)),0)) * 100, 1) AS variacao_pct
FROM base
GROUP BY descricao_subsetor
HAVING eleg_2022 > 0
ORDER BY eleg_2022 DESC
LIMIT 15
""")
print(df3.to_string(index=False))

# 4. Top cargos elegíveis (2022)
print('\n[4] TOP 20 CARGOS COM MAIOR VOLUME ELEGÍVEL (2022)')
print('-'*80)
df4 = q(f"""
SELECT
  descricao_cargo,
  SUM(total_vinculos) AS total_vinculos,
  ROUND(SAFE_DIVIDE(SUM(total_vinculos*salario_medio_reais), SUM(total_vinculos)),2) AS salario_medio,
  SUM(IF(salario_medio_reais >= {RENDA_MIN}, total_vinculos, 0)) AS elegiveis
FROM `{PROJECT}.raw_facts.fct_empregos`
WHERE id_municipio = '{ID_MUNICIPIO}' AND ano = 2022 AND descricao_cargo IS NOT NULL
GROUP BY descricao_cargo
HAVING elegiveis > 0
ORDER BY elegiveis DESC
LIMIT 20
""")
print(df4.to_string(index=False))

# 5. Cargos em ascensão entre os elegíveis
print('\n[5] TOP 15 CARGOS ELEGÍVEIS EM ASCENSÃO (Δ% 2020→2022, vol mín 50)')
print('-'*80)
df5 = q(f"""
WITH base AS (
  SELECT ano, descricao_cargo,
    SUM(IF(salario_medio_reais >= {RENDA_MIN}, total_vinculos, 0)) AS elegiveis,
    ROUND(SAFE_DIVIDE(SUM(total_vinculos*salario_medio_reais), SUM(total_vinculos)),2) AS sal_med
  FROM `{PROJECT}.raw_facts.fct_empregos`
  WHERE id_municipio = '{ID_MUNICIPIO}' AND ano IN (2020, 2022) AND descricao_cargo IS NOT NULL
  GROUP BY ano, descricao_cargo
)
SELECT
  descricao_cargo,
  MAX(IF(ano=2020, elegiveis, NULL)) AS eleg_2020,
  MAX(IF(ano=2022, elegiveis, NULL)) AS eleg_2022,
  MAX(IF(ano=2022, sal_med, NULL))   AS salario_medio,
  ROUND(SAFE_DIVIDE(
    MAX(IF(ano=2022, elegiveis, NULL)) - MAX(IF(ano=2020, elegiveis, NULL)),
    NULLIF(MAX(IF(ano=2020, elegiveis, NULL)),0)) * 100, 1) AS variacao_pct
FROM base
GROUP BY descricao_cargo
HAVING eleg_2022 >= 50
ORDER BY variacao_pct DESC
LIMIT 15
""")
print(df5.to_string(index=False))

# 6. Cargos elegíveis em queda
print('\n[6] TOP 15 CARGOS ELEGÍVEIS EM QUEDA')
print('-'*80)
df6 = q(f"""
WITH base AS (
  SELECT ano, descricao_cargo,
    SUM(IF(salario_medio_reais >= {RENDA_MIN}, total_vinculos, 0)) AS elegiveis
  FROM `{PROJECT}.raw_facts.fct_empregos`
  WHERE id_municipio = '{ID_MUNICIPIO}' AND ano IN (2020, 2022) AND descricao_cargo IS NOT NULL
  GROUP BY ano, descricao_cargo
)
SELECT
  descricao_cargo,
  MAX(IF(ano=2020, elegiveis, NULL)) AS eleg_2020,
  MAX(IF(ano=2022, elegiveis, NULL)) AS eleg_2022,
  ROUND(SAFE_DIVIDE(
    MAX(IF(ano=2022, elegiveis, NULL)) - MAX(IF(ano=2020, elegiveis, NULL)),
    NULLIF(MAX(IF(ano=2020, elegiveis, NULL)),0)) * 100, 1) AS variacao_pct
FROM base
GROUP BY descricao_cargo
HAVING eleg_2020 >= 50 AND eleg_2022 < eleg_2020
ORDER BY variacao_pct ASC
LIMIT 15
""")
print(df6.to_string(index=False))

# 7. Densidade empresarial dos setores elegíveis (2023)
print('\n[7] DENSIDADE EMPRESARIAL — TOP SETORES ELEGÍVEIS (2023)')
print('-'*80)
df7 = q(f"""
WITH eleg AS (
  SELECT subsetor_ibge, descricao_subsetor,
    SUM(IF(salario_medio_reais >= {RENDA_MIN}, total_vinculos, 0)) AS elegiveis
  FROM `{PROJECT}.raw_facts.fct_empregos`
  WHERE id_municipio = '{ID_MUNICIPIO}' AND ano = 2022
  GROUP BY 1,2
  HAVING elegiveis > 0
),
estab AS (
  SELECT subsetor_ibge,
    SUM(total_estabelecimentos) AS estabs,
    SUM(total_vinculos_ativos)  AS vinculos_ativos
  FROM `{PROJECT}.raw_facts.fct_estabelecimentos`
  WHERE id_municipio = '{ID_MUNICIPIO}' AND ano = 2023
  GROUP BY 1
)
SELECT e.descricao_subsetor, e.elegiveis,
       s.estabs, s.vinculos_ativos,
       ROUND(SAFE_DIVIDE(s.vinculos_ativos, NULLIF(s.estabs,0)),1) AS func_por_estab,
       ROUND(SAFE_DIVIDE(e.elegiveis, NULLIF(s.estabs,0)),1)       AS elegiveis_por_estab
FROM eleg e LEFT JOIN estab s USING(subsetor_ibge)
ORDER BY e.elegiveis DESC LIMIT 15
""")
print(df7.to_string(index=False))

# 8. Pipeline universitário — graduados que poderiam virar pós
print('\n[8] FORMANDOS GRADUAÇÃO (último ano) — POTENCIAL PÓS')
print('-'*80)
df8 = q(f"""
WITH ano_max AS (SELECT MAX(ano) AS ano FROM `{PROJECT}.raw_facts.fct_mercado_superior` WHERE id_municipio = '{ID_MUNICIPIO}')
SELECT
  m.nome_area_geral,
  SUM(m.total_concluintes) AS concluintes,
  COUNT(DISTINCT m.id_curso) AS cursos,
  COUNT(DISTINCT m.id_ies)   AS ies
FROM `{PROJECT}.raw_facts.fct_mercado_superior` m
JOIN ano_max a ON m.ano = a.ano
WHERE m.id_municipio = '{ID_MUNICIPIO}'
GROUP BY 1 ORDER BY concluintes DESC
""")
print(df8.to_string(index=False))

print('\n' + '='*80)
print('FIM DA ANÁLISE')
print('='*80)
