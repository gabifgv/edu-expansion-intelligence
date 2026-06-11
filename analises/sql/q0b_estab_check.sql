SELECT id_municipio, ano,
       SUM(total_estabelecimentos) AS total_estabs,
       SUM(total_vinculos_ativos) AS total_vinc_ativos
FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_estabelecimentos`
WHERE id_municipio IN ('3509502', '3525904', '3538709', '3552205')
  AND ano BETWEEN 2020 AND 2024
GROUP BY id_municipio, ano
ORDER BY id_municipio, ano;
