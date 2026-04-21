# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

TCC (MBA capstone) — MLOps + GenAI pipeline for educational market intelligence in Brazil. The goal is to cluster Brazilian municipalities by socioeconomic and educational profile, then use Gemini to generate strategic insights for FGV campus expansion decisions.

**GCP project:** `project-a8f8452a-3033-4dd8-99a`
**BigQuery dataset (raw sources):** `raw`
**dbt profile:** `inteligencia_expansao_educacional` (BigQuery, OAuth, US region)

## Common commands

```bash
dbt parse                          # Validate project config and models (no BQ connection needed)
dbt debug                          # Test BigQuery connection
dbt run --select staging           # Run all staging models
dbt test --select staging          # Run all staging tests
dbt run --select marts             # Run all mart models
dbt run --select <model_name>      # Run a single model
dbt test --select <model_name>     # Test a single model
dbt docs generate && dbt docs serve  # Generate and serve lineage docs
```

## Architecture

```
BigQuery raw dataset (source tables)
        ↓
dbt staging (views)     — type casting, column renaming, classification bands, null filters
        ↓
dbt marts (tables)      — municipality-level aggregations, funnel metrics, ML feature table
        ↓
Vertex AI               — unsupervised clustering (K-Means)
        ↓
Gemini + LangChain      — natural language strategic insights
```

**Current status:** Staging complete (P3). Marts and ML pipeline (P4–P5) in progress.

## dbt layer conventions

- **Staging** (`models/staging/`): Views. One model per source table. File naming: `stg_[source]_[entity].sql`. Handles casting, trimming, CASE decoding, and filters only. No joins.
- **Marts** (`models/marts/`): Tables. File naming: `mart_[entity].sql` for aggregated facts, `dim_[dimension].sql` for dimensions. Business logic and cross-source joins live here.
- **Raw** (`models/raw/`): Not yet implemented. Planned as thin views over source tables.

## Data sources and join keys

All 6 sources share `id_municipio` (IBGE 7-digit code) + `ano` as the common grain for municipality-level joins:

| Staging model | Source table | Grain |
|---|---|---|
| `stg_inep_graduacao` | higher education census | course × IES × municipality × year |
| `stg_inse_escola` | school socioeconomic index | school × year |
| `stg_ideb_escola` | school quality index (high school only) | school × year |
| `stg_inep_formandos_ensinomedio` | high school graduates | school × municipality × year |
| `stg_rais_vinculos_municipio` | formal employment | municipality × sector × CNAE × year |
| `stg_munic_socio_educ` | municipal HDI, income, population | municipality × year |

## Key mart to build next

`mart_municipio_perfil` — the central ML feature table. Aggregates all 6 staging models to municipality grain. This table feeds directly into Vertex AI clustering. Features include: `idhm`, `renda_per_capita`, `populacao_18_24`, `taxa_freq_bruta_superior`, `salario_medio_reais`, `total_matriculas_ies`, `ideb_medio_municipio`, `pct_escolas_inse_alto`, `indice_gini`.

## dbt test syntax (dbt 1.9+)

Use `arguments:` nesting for generic test parameters — this project is on dbt 1.11:

```yaml
- accepted_values:
    arguments:
      values: ['Presencial', 'EAD']
```

Use `data_tests:` (not `tests:`) for column-level tests.

## BigQuery notes

- Raw source tables may have schema changes made directly in BigQuery (e.g., new columns added). Always check `sources.yml` and the corresponding staging model when a source column is referenced that isn't yet declared.
- `profiles.yml` uses OAuth — run `gcloud auth application-default login` if authentication fails.
