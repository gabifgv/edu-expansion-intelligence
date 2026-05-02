{{
  config(
    materialized='table'
  )
}}

select
    -- temporal (bienal: 2020, 2021, 2023)
    ano,

    -- chaves
    id_escola,
    id_municipio,

    -- classificação
    rede,
    ensino,
    anos_escolares,

    -- métricas de desempenho acadêmico
    taxa_aprovacao,
    nota_saeb_matematica,
    nota_saeb_lingua_portuguesa,
    nota_saeb_media_padronizada,
    ideb,
    faixa_ideb

from {{ ref('stg_ideb_escola') }}
