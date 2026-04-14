{{
  config(
    materialized='view'
  )
}}

with source as (
    select * from {{ source('raw', 'ideb_escola') }}
),

renamed as (
    select
        -- chaves
        cast(ano            as integer)  as ano,
        trim(id_escola)                  as id_escola,
        trim(id_municipio)               as id_municipio,

        -- classificação
        trim(rede)                       as rede,
        trim(ensino)                     as ensino,
        trim(anos_escolares)             as anos_escolares,

        -- métricas de desempenho
        cast(taxa_aprovacao               as float64) as taxa_aprovacao,
        cast(nota_saeb_matematica         as float64) as nota_saeb_matematica,
        cast(nota_saeb_lingua_portuguesa  as float64) as nota_saeb_lingua_portuguesa,
        cast(nota_saeb_media_padronizada  as float64) as nota_saeb_media_padronizada,
        cast(ideb                         as float64) as ideb,

        -- flag de qualidade para uso nos marts
        case
            when cast(ideb as float64) >= 7.0 then 'Excelente'
            when cast(ideb as float64) >= 6.0 then 'Alto'
            when cast(ideb as float64) >= 4.0 then 'Médio'
            else 'Baixo'
        end as faixa_ideb

    from source
    where id_escola is not null
      and ideb is not null
      and ensino = 'medio'
)

select * from renamed
