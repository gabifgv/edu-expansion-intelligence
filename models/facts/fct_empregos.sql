{{
  config(
    materialized='table'
  )
}}

select
    -- temporal
    ano,

    -- chaves geográficas
    id_municipio,
    sigla_uf,

    -- setor econômico
    subsetor_ibge,
    descricao_subsetor,
    cnae_2,
    descricao_cnae,

    -- cargo / ocupação
    cbo_2002,
    descricao_cargo,

    -- métricas de mercado de trabalho
    total_vinculos,
    salario_medio_reais,
    salario_medio_sm

from {{ ref('stg_rais_vinculos_municipio') }}
