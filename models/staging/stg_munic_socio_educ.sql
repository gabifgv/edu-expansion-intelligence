{{
  config(
    materialized='view'
  )
}}

with source as (
    select * from {{ source('raw', 'munic_socio_educ') }}
),

renamed as (
    select
        -- chaves
        cast(ano            as integer)  as ano,
        trim(id_municipio)               as id_municipio,

        -- índices de desenvolvimento
        cast(idhm   as float64)          as idhm,
        cast(idhm_e as float64)          as idhm_educacao,
        cast(idhm_r as float64)          as idhm_renda,

        -- renda e desigualdade
        cast(renda_pc     as float64)    as renda_per_capita,
        cast(indice_gini  as float64)    as indice_gini,

        -- população
        cast(populacao         as integer) as populacao_total,
        cast(populacao_urbana  as integer) as populacao_urbana,
        cast(populacao_15_17   as integer) as populacao_15_17,
        cast(populacao_16_18   as integer) as populacao_16_18,
        cast(populacao_18_24   as integer) as populacao_18_24,

        -- taxas educacionais
        cast(taxa_freq_liquida_medio   as float64) as taxa_freq_liquida_medio,
        cast(taxa_freq_bruta_superior  as float64) as taxa_freq_bruta_superior,
        cast(taxa_medio_18_24          as float64) as taxa_medio_18_24,
        cast(taxa_superior_25_mais     as float64) as taxa_superior_25_mais,

        -- vulnerabilidade
        cast(prop_pobreza as float64)    as prop_pobreza,

        -- faixa IDHM para segmentação nos marts
        case
            when cast(idhm as float64) >= 0.900 then 'Muito Alto'
            when cast(idhm as float64) >= 0.800 then 'Alto'
            when cast(idhm as float64) >= 0.700 then 'Médio'
            when cast(idhm as float64) >= 0.550 then 'Baixo'
            else 'Muito Baixo'
        end as faixa_idhm

    from source
    where id_municipio is not null
      and idhm is not null
)

select * from renamed
