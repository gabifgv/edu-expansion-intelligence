{{
  config(
    materialized='table'
  )
}}

select
    -- temporal (snapshot 2023)
    ano,

    -- chaves
    id_escola,
    id_municipio,
    sigla_uf,
    nome_municipio,
    nome_escola,

    -- classificação da rede
    rede_codigo,
    rede,

    -- localização geográfica
    latitude,
    longitude,

    -- indicador socioeconômico
    inse_valor,
    inse_classificacao,
    quantidade_alunos_inse

from {{ ref('stg_inse_escola') }}
