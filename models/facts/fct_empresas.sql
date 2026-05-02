{{
  config(
    materialized='table'
  )
}}

select
    -- chaves (sem ano — snapshot Receita Federal)
    cnpj,
    cnpj_basico,
    id_municipio,
    sigla_uf,

    -- identificação
    nome_empresa,
    razao_social,

    -- atividade econômica
    cnae_fiscal_principal,
    cnae_classe,

    -- localização e contato
    cep,
    ddd,
    telefone,
    email,

    -- dados cadastrais
    data_inicio_atividade,
    natureza_juridica,
    porte,
    capital_social

from {{ ref('stg_cnpj_empresas') }}
