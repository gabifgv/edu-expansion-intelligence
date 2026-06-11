WITH base AS (
  SELECT id_municipio, ano, cbo_2002, descricao_cargo,
         SUM(total_vinculos) AS vinculos,
         ROUND(SAFE_DIVIDE(
             SUM(total_vinculos * salario_medio_reais),
             NULLIF(SUM(total_vinculos), 0)
         ), 2) AS salario_medio,
         SUM(CASE WHEN salario_medio_reais >= 13863.16 THEN total_vinculos ELSE 0 END) AS vinc_eleg
  FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empregos`
  WHERE id_municipio IN ('3509502', '3525904', '3538709', '3552205')
    AND ano BETWEEN 2020 AND 2022
  GROUP BY id_municipio, ano, cbo_2002, descricao_cargo
),
pivot AS (
  SELECT id_municipio, cbo_2002, descricao_cargo,
         MAX(IF(ano = 2020, vinculos, NULL))      AS vinc_2020,
         MAX(IF(ano = 2021, vinculos, NULL))      AS vinc_2021,
         MAX(IF(ano = 2022, vinculos, NULL))      AS vinc_2022,
         MAX(IF(ano = 2020, salario_medio, NULL)) AS sal_2020,
         MAX(IF(ano = 2021, salario_medio, NULL)) AS sal_2021,
         MAX(IF(ano = 2022, salario_medio, NULL)) AS sal_2022,
         MAX(IF(ano = 2020, vinc_eleg, NULL))     AS eleg_2020,
         MAX(IF(ano = 2021, vinc_eleg, NULL))     AS eleg_2021,
         MAX(IF(ano = 2022, vinc_eleg, NULL))     AS eleg_2022
  FROM base
  GROUP BY id_municipio, cbo_2002, descricao_cargo
)
SELECT
  id_municipio, cbo_2002, descricao_cargo,
  COALESCE(vinc_2020, 0) AS vinc_2020,
  COALESCE(vinc_2021, 0) AS vinc_2021,
  COALESCE(vinc_2022, 0) AS vinc_2022,
  sal_2020, sal_2021, sal_2022,
  COALESCE(eleg_2020, 0) AS eleg_2020,
  COALESCE(eleg_2021, 0) AS eleg_2021,
  COALESCE(eleg_2022, 0) AS eleg_2022,
  ROUND(SAFE_DIVIDE(COALESCE(vinc_2022, 0) - COALESCE(vinc_2020, 0), NULLIF(vinc_2020, 0)) * 100, 1) AS delta_vinc_pct,
  ROUND(SAFE_DIVIDE(COALESCE(eleg_2022, 0) - COALESCE(eleg_2020, 0), NULLIF(eleg_2020, 0)) * 100, 1) AS delta_eleg_pct
FROM pivot
WHERE COALESCE(eleg_2022, 0) > 0
ORDER BY id_municipio, eleg_2022 DESC, vinc_2022 DESC;
