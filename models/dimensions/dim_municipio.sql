{{
  config(
    materialized='table'
  )
}}

with municipios as (
    select distinct
        id_municipio,
        nome_municipio,
        sigla_uf
    from {{ ref('stg_inep_formandos_ensinomedio') }}
),

socio as (
    select * from {{ ref('stg_munic_socio_educ') }}
)

select
    m.id_municipio,
    m.nome_municipio,
    m.sigla_uf,

    -- índices de desenvolvimento humano
    s.idhm,
    s.idhm_educacao,
    s.idhm_renda,
    s.faixa_idhm,

    -- renda e desigualdade
    s.renda_per_capita,
    s.indice_gini,

    -- população
    s.populacao_total,
    s.populacao_urbana,
    s.populacao_15_17,
    s.populacao_16_18,
    s.populacao_18_24,

    -- taxas educacionais
    s.taxa_freq_liquida_medio,
    s.taxa_freq_bruta_superior,
    s.taxa_medio_18_24,
    s.taxa_superior_25_mais,

    -- vulnerabilidade
    s.prop_pobreza

from municipios m
left join socio s on m.id_municipio = s.id_municipio
