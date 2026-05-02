{{
  config(
    materialized='view'
  )
}}

with source as (
    select * from {{ source('raw', 'cnpj_empresas') }}
),

renamed as (
    select
        -- chaves
        trim(cnpj)                              as cnpj,
        trim(cnpj_basico)                       as cnpj_basico,

        -- identificação
        trim(nome_empresa)                      as nome_empresa,
        trim(razao_social)                      as razao_social,

        -- atividade econômica
        trim(cnae_fiscal_principal)             as cnae_fiscal_principal,
        trim(cnae_classe)                       as cnae_classe,

        -- localização
        trim(id_municipio)                      as id_municipio,
        trim(sigla_uf)                          as sigla_uf,
        nullif(trim(cep), '')                   as cep,

        -- contato
        nullif(trim(ddd), '')                   as ddd,
        nullif(trim(telefone), '')              as telefone,
        nullif(trim(email), '')                 as email,

        -- temporalidade
        date(data_inicio_atividade)             as data_inicio_atividade,

        -- porte e capacidade financeira
        trim(natureza_juridica)                 as natureza_juridica,
        trim(porte)                             as porte,
        cast(capital_social as float64)         as capital_social

    from source
    where cnpj_basico is not null
      and razao_social is not null
      and id_municipio is not null
)

select * from renamed
