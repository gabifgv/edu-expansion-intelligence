{{
  config(
    materialized='view'
  )
}}

with source as (
    select * from {{ source('raw', 'inep_graduacao') }}
),

renamed as (
    select
        -- chaves
        cast(ano              as integer)  as ano,
        trim(sigla_uf)                     as sigla_uf,
        trim(id_municipio)                 as id_municipio,
        trim(nome_municipio)               as nome_municipio,

        -- instituição
        trim(id_ies)                       as id_ies,
        trim(sigla_ies)                    as sigla_ies,
        trim(nome_ies)                     as nome_ies,
        trim(nome_mantenedora)             as nome_mantenedora,
        trim(rede)                         as rede,
        trim(modalidade_ensino)            as modalidade_ensino,

        -- área de conhecimento
        trim(nome_area_geral)              as nome_area_geral,
        trim(nome_area_especifica)         as nome_area_especifica,
        trim(nome_area_detalhada)          as nome_area_detalhada,

        -- métricas
        cast(total_vagas           as integer) as total_vagas,
        cast(total_vagas_ead       as integer) as total_vagas_ead,
        cast(total_inscritos       as integer) as total_inscritos,
        cast(total_inscritos_ead   as integer) as total_inscritos_ead,
        cast(total_ingressantes    as integer) as total_ingressantes,
        cast(total_matriculas      as integer) as total_matriculas,
        cast(total_concluintes     as integer) as total_concluintes

    from source
    where ano is not null
      and id_municipio is not null
)

select * from renamed
