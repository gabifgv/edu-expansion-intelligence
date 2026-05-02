{{
  config(
    materialized='table'
  )
}}

select
    -- temporal
    ano,

    -- chaves geográficas
    id_municipio,
    sigla_uf,
    nome_municipio,

    -- instituição
    id_ies,
    nome_ies,
    sigla_ies,
    rede,
    modalidade_ensino,

    -- curso (área INEP)
    id_curso,
    nome_area_geral,
    nome_area_especifica,
    nome_area_detalhada,

    -- métricas de oferta e demanda
    total_vagas,
    total_vagas_ead,
    total_inscritos,
    total_inscritos_ead,
    total_ingressantes,
    total_matriculas,
    total_concluintes

from {{ ref('stg_inep_graduacao') }}
