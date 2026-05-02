{{
  config(
    materialized='view'
  )
}}

with inep as (
    select * from {{ ref('stg_inep_graduacao') }}
),

depara as (
    select * from {{ ref('fgv_depara') }}
),

joined as (
    select
        inep.ano,
        inep.sigla_uf,
        inep.id_municipio,
        inep.nome_municipio,
        inep.modalidade_ensino,

        -- instituição
        inep.id_ies,
        inep.nome_ies,
        inep.sigla_ies,
        inep.rede,

        -- curso INEP (área)
        inep.id_curso,
        inep.nome_area_geral,
        inep.nome_area_especifica,
        inep.nome_area_detalhada,

        -- metadados do depara FGV
        dep.grupo_ies,
        dep.curso_agrupado_fgv,
        dep.no_curso            as nome_curso_depara,
        dep.praca_fgv,
        dep.escola_fgv,
        dep.sigla_ies           as sigla_ies_grupo,

        -- métricas de valor
        inep.total_vagas,
        inep.total_vagas_ead,
        inep.total_inscritos,
        inep.total_inscritos_ead,
        inep.total_ingressantes,
        inep.total_matriculas,
        inep.total_concluintes

    from inep
    inner join depara dep
        on inep.id_curso = cast(dep.co_curso as string)

    where
        -- FGV: apenas presencial (naturalmente em SP, RJ e DF)
        (dep.grupo_ies = 'FGV' and inep.modalidade_ensino = 'Presencial')
        or
        -- Concorrentes: apenas nos municípios onde a FGV opera
        (dep.grupo_ies != 'FGV' and inep.id_municipio in (
            '3550308',  -- São Paulo
            '3304557',  -- Rio de Janeiro
            '5300108'   -- Brasília
        ))
)

select * from joined
