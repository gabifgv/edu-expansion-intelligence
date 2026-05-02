{{
  config(
    materialized='view'
  )
}}

with source as (
    select * from {{ source('raw', 'rais_estabelecimentos_municipio') }}
    where ano >= 2020
),

renamed as (
    select
        -- chaves
        cast(ano           as integer) as ano,
        trim(sigla_uf)                 as sigla_uf,
        trim(id_municipio)             as id_municipio,

        -- setor econômico
        cast(subsetor_ibge as integer) as subsetor_ibge,
        case cast(subsetor_ibge as integer)
            when 1  then 'Extrativismo Mineral'
            when 2  then 'Indústria de Produtos Minerais Não Metálicos'
            when 3  then 'Indústria Metalúrgica'
            when 4  then 'Indústria Mecânica'
            when 5  then 'Indústria do Material Elétrico e de Comunicações'
            when 6  then 'Indústria do Material de Transporte'
            when 7  then 'Indústria da Madeira e do Mobiliário'
            when 8  then 'Indústria do Papel, Papelão, Editorial e Gráfica'
            when 9  then 'Indústria da Borracha, Fumo, Couros e Similares'
            when 10 then 'Indústria Química'
            when 11 then 'Indústria Têxtil do Vestuário e Artefatos de Tecidos'
            when 12 then 'Indústria de Calçados'
            when 13 then 'Indústria de Produtos Alimentícios, Bebidas e Álcool'
            when 14 then 'Serviços Industriais de Utilidade Pública'
            when 15 then 'Construção Civil'
            when 16 then 'Comércio Varejista'
            when 17 then 'Comércio Atacadista'
            when 18 then 'Instituições de Crédito, Seguros e Capitalização'
            when 19 then 'Comércio e Administração de Imóveis e Serviços Técnicos'
            when 20 then 'Transportes e Comunicações'
            when 21 then 'Serviços de Alojamento, Alimentação e Reparação'
            when 22 then 'Serviços Médicos, Odontológicos e Veterinários'
            when 23 then 'Ensino'
            when 24 then 'Administração Pública Direta e Autárquica'
            when 25 then 'Agricultura, Silvicultura, Criação de Animais e Extrativismo Vegetal'
            else        'Não Classificado'
        end                            as descricao_subsetor,
        trim(cnae_2_subclasse)         as cnae_2_subclasse,
        trim(cnae_2)                   as cnae_2,
        trim(descricao_cnae)           as descricao_cnae,

        -- métricas
        cast(total_estabelecimentos as integer) as total_estabelecimentos,
        cast(total_vinculos_ativos  as integer) as total_vinculos_ativos

    from source
    where id_municipio is not null
)

select * from renamed
