SELECT id_municipio, nome_municipio, sigla_uf
FROM `project-a8f8452a-3033-4dd8-99a.raw_dimensions.dim_municipio`
WHERE sigla_uf = 'SP'
  AND (nome_municipio = 'Campinas'
    OR nome_municipio = 'Piracicaba'
    OR nome_municipio = 'Sorocaba'
    OR nome_municipio LIKE 'Jundia%')
ORDER BY nome_municipio;
