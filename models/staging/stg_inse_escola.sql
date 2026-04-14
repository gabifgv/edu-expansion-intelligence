{{
  config(
    materialized='view'
  )
}}

with source as (
    select * from {{ source('raw', 'inse_escola') }}
),

renamed as (
    select
        -- chaves
        cast(ano            as integer)  as ano,
        trim(sigla_uf)                   as sigla_uf,
        trim(id_municipio)               as id_municipio,
        trim(nome_municipio)             as nome_municipio,
        trim(id_escola)                  as id_escola,
        trim(nome_escola)                as nome_escola,

        -- rede
        cast(rede as integer)            as rede_codigo,
        case cast(rede as integer)
            when 1 then 'Federal'
            when 2 then 'Estadual'
            when 3 then 'Municipal'
            when 4 then 'Privada'
            else 'Não informado'
        end                              as rede,

        -- localização geográfica
        cast(latitude  as float64)       as latitude,
        cast(longitude as float64)       as longitude,

        -- indicador socioeconômico
        cast(inse as float64)            as inse_valor,
        trim(classificacao)              as inse_classificacao,
        cast(quantidade_alunos_inse as integer) as quantidade_alunos_inse

    from source
    where id_escola is not null
      and inse is not null
)

select * from renamed
