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
    cnae_2_subclasse,
    cnae_2,
    descricao_cnae,

    -- métricas de densidade empresarial
    total_estabelecimentos,
    total_vinculos_ativos

from {{ ref('stg_rais_estabelecimentos_municipio') }}
