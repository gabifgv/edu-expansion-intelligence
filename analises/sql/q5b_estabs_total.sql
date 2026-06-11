-- Total de estabelecimentos por cidade (snapshot 2024 + delta 2020->2024)
WITH agg AS (
  SELECT id_municipio, ano,
         SUM(total_estabelecimentos) AS estabs,
         SUM(total_vinculos_ativos)  AS vinc_ativos
  FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_estabelecimentos`
  WHERE id_municipio IN ('3509502', '3525904', '3538709', '3552205')
    AND ano IN (2020, 2021, 2023, 2024)
  GROUP BY id_municipio, ano
)
SELECT id_municipio,
       MAX(IF(ano=2020, estabs, NULL)) AS estabs_2020,
       MAX(IF(ano=2021, estabs, NULL)) AS estabs_2021,
       MAX(IF(ano=2023, estabs, NULL)) AS estabs_2023,
       MAX(IF(ano=2024, estabs, NULL)) AS estabs_2024,
       MAX(IF(ano=2020, vinc_ativos, NULL)) AS vinc_ativos_2020,
       MAX(IF(ano=2024, vinc_ativos, NULL)) AS vinc_ativos_2024
FROM agg
GROUP BY id_municipio
ORDER BY id_municipio;
