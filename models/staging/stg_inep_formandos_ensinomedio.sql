{{
  config(
    materialized='view'
  )
}}

with source as (
    select * from {{ source('raw', 'inep_formandos_ensinomedio') }}
),

renamed as (
    select
        -- chaves
        cast(ano            as integer)  as ano,
        trim(sigla_uf)                   as sigla_uf,
        trim(id_municipio)               as id_municipio,
        trim(nome_municipio)             as nome_municipio,
        trim(id_escola)                  as id_escola,

        -- classificação
        trim(tipo_rede)                  as tipo_rede,

        -- métricas
        cast(total_formandos as integer) as total_formandos

    from source
    where id_escola is not null
      and ano is not null
      and total_formandos > 0
)

select * from renamed
