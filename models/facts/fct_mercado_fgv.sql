{{
  config(
    materialized='table'
  )
}}

select
    -- temporal
    ano,

    -- chaves geográficas (SP, RJ ou DF)
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

    -- metadados FGV (do seed fgv_depara)
    grupo_ies,
    sigla_ies_grupo,
    curso_agrupado_fgv,
    nome_curso_depara,
    praca_fgv,
    escola_fgv,

    -- flag pública vs privada (derivado do rede INEP)
    case
        when rede like 'Pública%' then 'Pública'
        else 'Privada'
    end as tipo_instituicao,

    -- métricas de oferta e demanda
    total_vagas,
    total_vagas_ead,
    total_inscritos,
    total_inscritos_ead,
    total_ingressantes,
    total_matriculas,
    total_concluintes

from {{ ref('stg_inep_graduacao_fgv') }}
