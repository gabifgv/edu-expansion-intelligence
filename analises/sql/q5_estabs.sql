-- Q5a: snapshot 2024 por setor, com join em vínculos elegíveis 2022
WITH estab_2024 AS (
  SELECT id_municipio, descricao_subsetor,
         SUM(total_estabelecimentos) AS estabs_2024,
         SUM(total_vinculos_ativos)  AS vinc_ativos_2024
  FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_estabelecimentos`
  WHERE id_municipio IN ('3509502', '3525904', '3538709', '3552205')
    AND ano = 2024
  GROUP BY id_municipio, descricao_subsetor
),
estab_2020 AS (
  SELECT id_municipio, descricao_subsetor,
         SUM(total_estabelecimentos) AS estabs_2020
  FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_estabelecimentos`
  WHERE id_municipio IN ('3509502', '3525904', '3538709', '3552205')
    AND ano = 2020
  GROUP BY id_municipio, descricao_subsetor
),
vinc_2022 AS (
  SELECT id_municipio, descricao_subsetor,
         SUM(total_vinculos) AS vinc_total,
         SUM(CASE WHEN salario_medio_reais >= 13863.16 THEN total_vinculos ELSE 0 END) AS vinc_eleg
  FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empregos`
  WHERE id_municipio IN ('3509502', '3525904', '3538709', '3552205')
    AND ano = 2022
  GROUP BY id_municipio, descricao_subsetor
)
SELECT
  e.id_municipio,
  e.descricao_subsetor,
  COALESCE(e0.estabs_2020, 0) AS estabs_2020,
  e.estabs_2024,
  ROUND(SAFE_DIVIDE(e.estabs_2024 - COALESCE(e0.estabs_2020, 0), NULLIF(e0.estabs_2020, 0)) * 100, 1) AS delta_estabs_pct,
  e.vinc_ativos_2024,
  COALESCE(v.vinc_total, 0) AS vinc_total_2022,
  COALESCE(v.vinc_eleg, 0)  AS vinc_eleg_2022,
  ROUND(SAFE_DIVIDE(COALESCE(v.vinc_eleg, 0), NULLIF(v.vinc_total, 0)) * 100, 1) AS pct_eleg_2022
FROM estab_2024 e
LEFT JOIN estab_2020 e0 USING (id_municipio, descricao_subsetor)
LEFT JOIN vinc_2022   v USING (id_municipio, descricao_subsetor)
ORDER BY e.id_municipio, e.estabs_2024 DESC;
