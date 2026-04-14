{{
  config(
    materialized='view'
  )
}}

with source as (
    select * from {{ source('raw', 'rais_vinculos_municipio') }}
),

renamed as (
    select
        -- chaves
        cast(ano            as integer)  as ano,
        trim(sigla_uf)                   as sigla_uf,
        trim(id_municipio)               as id_municipio,

        -- setor econômico
        cast(subsetor_ibge  as integer)  as subsetor_ibge,
        trim(descricao_subsetor)         as descricao_subsetor,
        trim(cnae_2)                     as cnae_2,
        trim(descricao_cnae)             as descricao_cnae,

        -- métricas de mercado de trabalho
        cast(total_vinculos          as integer) as total_vinculos,
        cast(total_estabelecimentos  as integer) as total_estabelecimentos,
        cast(salario_medio           as float64) as salario_medio_reais,
        cast(salario_medio_sm        as float64) as salario_medio_sm

    from source
    where id_municipio is not null
      and ano is not null
      and total_vinculos > 0
)

select * from renamed
