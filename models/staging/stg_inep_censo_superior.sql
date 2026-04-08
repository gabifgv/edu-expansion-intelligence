{{
  config(
    materialized='view'
  )
}}

select
  ano,
  sigla_uf,
  id_municipio,
  nome_municipio,
  rede,
  modalidade_ensino,
  nome_ies,
  nome_area_geral,
  total_vagas,
  total_matriculas,
  total_concluintes
from {{ source('raw', 'inep_censo_superior') }}
