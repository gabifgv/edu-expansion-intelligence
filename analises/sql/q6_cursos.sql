WITH base AS (
  SELECT id_municipio, ano, nome_area_geral, nome_area_especifica, nome_area_detalhada,
         SUM(total_concluintes) AS concluintes,
         SUM(total_matriculas)  AS matriculas,
         SUM(total_ingressantes) AS ingressantes
  FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_mercado_superior`
  WHERE id_municipio IN ('3509502', '3525904', '3538709', '3552205')
    AND ano BETWEEN 2020 AND 2024
  GROUP BY id_municipio, ano, nome_area_geral, nome_area_especifica, nome_area_detalhada
),
pivot AS (
  SELECT id_municipio, nome_area_geral, nome_area_especifica, nome_area_detalhada,
         MAX(IF(ano = 2020, concluintes, NULL))  AS conc_2020,
         MAX(IF(ano = 2021, concluintes, NULL))  AS conc_2021,
         MAX(IF(ano = 2022, concluintes, NULL))  AS conc_2022,
         MAX(IF(ano = 2023, concluintes, NULL))  AS conc_2023,
         MAX(IF(ano = 2024, concluintes, NULL))  AS conc_2024,
         MAX(IF(ano = 2024, matriculas, NULL))   AS matr_2024,
         MAX(IF(ano = 2024, ingressantes, NULL)) AS ing_2024
  FROM base
  GROUP BY id_municipio, nome_area_geral, nome_area_especifica, nome_area_detalhada
)
SELECT
  id_municipio, nome_area_geral, nome_area_especifica, nome_area_detalhada,
  COALESCE(conc_2020, 0) AS conc_2020,
  COALESCE(conc_2021, 0) AS conc_2021,
  COALESCE(conc_2022, 0) AS conc_2022,
  COALESCE(conc_2023, 0) AS conc_2023,
  COALESCE(conc_2024, 0) AS conc_2024,
  COALESCE(matr_2024, 0) AS matr_2024,
  COALESCE(ing_2024, 0)  AS ing_2024,
  ROUND(SAFE_DIVIDE(COALESCE(conc_2024, 0) - COALESCE(conc_2020, 0), NULLIF(conc_2020, 0)) * 100, 1) AS delta_conc_pct
FROM pivot
WHERE COALESCE(conc_2024, 0) > 0 OR COALESCE(conc_2023, 0) > 0
ORDER BY id_municipio, conc_2024 DESC, conc_2023 DESC;
