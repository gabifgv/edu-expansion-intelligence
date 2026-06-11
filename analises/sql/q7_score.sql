-- Score de atratividade — 4 dimensões, 0-10 (alinhado com queries.py do dashboard)
-- D1: volume elegível normalizado pela pop. formada (cap 2.5)
-- D2: crescimento elegíveis 2020->2022 (cap 2.5)
-- D3: capacidade corporativa - mediana capital social (cap 2.5)
-- D4: renda relativa à UF (cap 2.5)
WITH vol AS (
  SELECT e.id_municipio,
         SUM(CASE WHEN e.salario_medio_reais >= 13863.16 THEN e.total_vinculos ELSE 0 END) AS elegiveis_2022,
         d.populacao_total,
         d.taxa_superior_25_mais
  FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empregos` e
  JOIN `project-a8f8452a-3033-4dd8-99a.raw_dimensions.dim_municipio` d USING (id_municipio)
  WHERE e.id_municipio IN ('3509502', '3525904', '3538709', '3552205')
    AND e.ano = 2022
  GROUP BY e.id_municipio, d.populacao_total, d.taxa_superior_25_mais
),
trend AS (
  SELECT id_municipio,
         MAX(IF(ano=2020, eleg, NULL)) AS eleg_2020,
         MAX(IF(ano=2022, eleg, NULL)) AS eleg_2022
  FROM (
    SELECT id_municipio, ano,
           SUM(CASE WHEN salario_medio_reais >= 13863.16 THEN total_vinculos ELSE 0 END) AS eleg
    FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empregos`
    WHERE id_municipio IN ('3509502', '3525904', '3538709', '3552205')
      AND ano IN (2020, 2022)
    GROUP BY id_municipio, ano
  )
  GROUP BY id_municipio
),
cap AS (
  SELECT id_municipio,
         APPROX_QUANTILES(capital_social, 2)[OFFSET(1)] AS mediana_cap
  FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empresas`
  WHERE id_municipio IN ('3509502', '3525904', '3538709', '3552205')
    AND capital_social > 0
  GROUP BY id_municipio
),
renda AS (
  SELECT d.id_municipio, d.renda_per_capita AS cidade_renda, uf.uf_renda
  FROM `project-a8f8452a-3033-4dd8-99a.raw_dimensions.dim_municipio` d
  CROSS JOIN (
    SELECT AVG(renda_per_capita) AS uf_renda
    FROM `project-a8f8452a-3033-4dd8-99a.raw_dimensions.dim_municipio`
    WHERE sigla_uf = 'SP'
  ) uf
  WHERE d.id_municipio IN ('3509502', '3525904', '3538709', '3552205')
)
SELECT
  v.id_municipio,
  -- D1: 5% penetração = 2.5 pts
  LEAST(2.5, GREATEST(0, ROUND(SAFE_DIVIDE(v.elegiveis_2022, NULLIF(v.populacao_total * v.taxa_superior_25_mais / 100, 0)) * 50, 2))) AS d1_volume,
  -- D2: 20% crescimento = 2.5 pts
  LEAST(2.5, GREATEST(0, ROUND(SAFE_DIVIDE(t.eleg_2022 - t.eleg_2020, NULLIF(t.eleg_2020, 0)) * 12.5, 2))) AS d2_crescimento,
  -- D3: R$10M mediana = 2.5 pts
  LEAST(2.5, GREATEST(0, ROUND(SAFE_DIVIDE(c.mediana_cap, 10000000) * 2.5, 2))) AS d3_capacidade,
  -- D4: (renda_cidade/renda_uf - 0.5) * 2.5
  LEAST(2.5, GREATEST(0, ROUND((SAFE_DIVIDE(r.cidade_renda, NULLIF(r.uf_renda, 0)) - 0.5) * 2.5, 2))) AS d4_renda
FROM vol v
LEFT JOIN trend t USING (id_municipio)
LEFT JOIN cap   c USING (id_municipio)
LEFT JOIN renda r USING (id_municipio)
ORDER BY v.id_municipio;
