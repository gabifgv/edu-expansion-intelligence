SELECT 'fct_empregos' AS tabela, MIN(ano) AS ano_min, MAX(ano) AS ano_max, COUNT(DISTINCT ano) AS n_anos
FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empregos`
UNION ALL
SELECT 'fct_estabelecimentos', MIN(ano), MAX(ano), COUNT(DISTINCT ano)
FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_estabelecimentos`
UNION ALL
SELECT 'fct_mercado_superior', MIN(ano), MAX(ano), COUNT(DISTINCT ano)
FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_mercado_superior`;
