{{
  config(
    materialized='table'
  )
}}

select
    -- temporal
    ano,

    -- chaves
    id_escola,
    id_municipio,
    sigla_uf,
    nome_municipio,

    -- classificação da escola
    tipo_rede,

    -- métrica de funil
    total_formandos

from {{ ref('stg_inep_formandos_ensinomedio') }}
