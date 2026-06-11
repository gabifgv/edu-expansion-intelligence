WITH base AS (
  SELECT id_municipio, ano, descricao_subsetor,
         SUM(total_vinculos) AS total_vinculos,
         SUM(CASE WHEN salario_medio_reais >= 13863.16 THEN total_vinculos ELSE 0 END) AS vinculos_elegiveis,
         ROUND(SAFE_DIVIDE(
             SUM(total_vinculos * salario_medio_reais),
             NULLIF(SUM(total_vinculos), 0)
         ), 2) AS salario_medio_pond
  FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empregos`
  WHERE id_municipio IN ('3509502', '3525904', '3538709', '3552205')
    AND ano BETWEEN 2020 AND 2022
  GROUP BY id_municipio, ano, descricao_subsetor
),
pivot AS (
  SELECT id_municipio, descricao_subsetor,
         MAX(IF(ano = 2020, total_vinculos, NULL))     AS total_2020,
         MAX(IF(ano = 2022, total_vinculos, NULL))     AS total_2022,
         MAX(IF(ano = 2020, vinculos_elegiveis, NULL)) AS eleg_2020,
         MAX(IF(ano = 2022, vinculos_elegiveis, NULL)) AS eleg_2022,
         MAX(IF(ano = 2022, salario_medio_pond, NULL)) AS sal_medio_2022
  FROM base
  GROUP BY id_municipio, descricao_subsetor
)
SELECT
  id_municipio, descricao_subsetor,
  total_2020, total_2022,
  eleg_2020, eleg_2022,
  sal_medio_2022,
  ROUND(SAFE_DIVIDE(eleg_2022, NULLIF(total_2022, 0)) * 100, 1) AS pct_eleg_2022,
  ROUND(SAFE_DIVIDE(total_2022 - total_2020, NULLIF(total_2020, 0)) * 100, 1) AS delta_total_pct,
  ROUND(SAFE_DIVIDE(eleg_2022 - eleg_2020, NULLIF(eleg_2020, 0)) * 100, 1) AS delta_eleg_pct
FROM pivot
WHERE total_2022 > 0
ORDER BY id_municipio, eleg_2022 DESC;
