SELECT
    id_municipio,
    ano,
    SUM(total_vinculos) AS total_vinculos,
    SUM(CASE WHEN salario_medio_reais >= 13863.16 THEN total_vinculos ELSE 0 END) AS vinculos_elegiveis,
    ROUND(SAFE_DIVIDE(
        SUM(total_vinculos * salario_medio_reais),
        NULLIF(SUM(total_vinculos), 0)
    ), 2) AS salario_medio_pond,
    ROUND(SAFE_DIVIDE(
        SUM(CASE WHEN salario_medio_reais >= 13863.16 THEN total_vinculos * salario_medio_reais ELSE 0 END),
        NULLIF(SUM(CASE WHEN salario_medio_reais >= 13863.16 THEN total_vinculos ELSE 0 END), 0)
    ), 2) AS salario_medio_elegiveis
FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empregos`
WHERE id_municipio IN ('3509502', '3525904', '3538709', '3552205')
  AND ano BETWEEN 2020 AND 2022
GROUP BY id_municipio, ano
ORDER BY id_municipio, ano;
