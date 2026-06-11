WITH cidades AS (
  SELECT id_municipio, nome_municipio, sigla_uf,
         idhm, renda_per_capita, indice_gini,
         populacao_total, populacao_urbana,
         taxa_superior_25_mais, prop_pobreza
  FROM `project-a8f8452a-3033-4dd8-99a.raw_dimensions.dim_municipio`
  WHERE id_municipio IN ('3509502', '3525904', '3538709', '3552205')
),
uf_avg AS (
  SELECT 'SP_media' AS id_municipio, 'Media SP' AS nome_municipio, 'SP' AS sigla_uf,
         ROUND(AVG(idhm), 3)                  AS idhm,
         ROUND(AVG(renda_per_capita), 2)      AS renda_per_capita,
         ROUND(AVG(indice_gini), 3)           AS indice_gini,
         ROUND(AVG(populacao_total), 0)       AS populacao_total,
         ROUND(AVG(populacao_urbana), 0)      AS populacao_urbana,
         ROUND(AVG(taxa_superior_25_mais), 2) AS taxa_superior_25_mais,
         ROUND(AVG(prop_pobreza), 2)          AS prop_pobreza
  FROM `project-a8f8452a-3033-4dd8-99a.raw_dimensions.dim_municipio`
  WHERE sigla_uf = 'SP'
)
SELECT * FROM cidades
UNION ALL
SELECT * FROM uf_avg
ORDER BY nome_municipio;
