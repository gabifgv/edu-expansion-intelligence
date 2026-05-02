# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

TCC (MBA capstone) — **FGV Market Intelligence Dashboard**. Real-time educational market analysis for campus expansion decisions. Combines institutional data (RAIS, INEP, IBGE) with Claude API for executive narratives.

**Product:** Interactive web dashboard analyzing municipality opportunity scores across 7 dimensions (socioeconomic profile, formal employment, corporate density, target companies, university pipeline, synthetic score, AI narrative).

**GCP project:** `project-a8f8452a-3033-4dd8-99a`
**BigQuery datasets:** `raw` (base), `raw_staging`, `raw_facts`, `raw_dimensions`
**dbt profile:** `inteligencia_expansao_educacional` (BigQuery, OAuth, US region)

## Stack

**Backend:** FastAPI (Python) + BigQuery
**Frontend:** HTML5 + Alpine.js + Plotly.js + Leaflet.js
**LLM:** Claude API (Anthropic) for narrative generation
**Infrastructure:** Cloud Run (planned) or local uvicorn

## Common commands

```bash
# dbt models
dbt parse
dbt debug
dbt run --select staging
dbt test --select staging
dbt run --select facts dimensions
dbt docs generate && dbt docs serve

# Dashboard
cd dashboard
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
# Open http://localhost:8000
```

## Architecture

```
Raw BigQuery tables (INEP, RAIS, IBGE, IDEB, INSE)
        ↓
dbt staging views       — casting, trimming, CASE decoding
        ↓
dbt dimensions + facts tables — star schema
        ↓
FastAPI backend queries
        ↓
HTML dashboard (7 blocks)
        ├─ Block 1: Perfil socioeconômico (vs UF)
        ├─ Block 2: Mercado de trabalho formal (RAIS)
        ├─ Block 3: Densidade empresarial por setor
        ├─ Block 4: Lista de empresas-alvo (CNPJ)
        ├─ Block 5: Formandos por IES e área (INEP)
        ├─ Block 6: Score de atratividade (4-dim)
        └─ Block 7: Narrativa AI (Claude)
```

**Current status:** Dashboard ✅ live. Data quality: CNAE field sparse in RAIS (99% null) — subsetor and cargo still usable.

## dbt layer conventions

- **Staging** (`models/staging/stg_*`): Views. One per source table. Cast, trim, CASE decode, filter only. No joins.
- **Dimensions** (`models/dimensions/dim_*`): Tables. Reference dimensions (e.g., `dim_municipio`). Single source of truth.
- **Facts** (`models/facts/fct_*`): Tables. Aggregated facts joined from staging. One row ≈ `(id_municipio, ano, setor, ...)` grain.

## dbt → BigQuery schema mapping

| dbt config | BQ dataset |
|---|---|
| `+schema: staging` | `raw_staging` |
| `+schema: dimensions` | `raw_dimensions` |
| `+schema: facts` | `raw_facts` |

Example: `select * from {{ref('fct_empregos')}}` → `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empregos`

## Data source grain

All sources join on `id_municipio` + `ano`:

| dbt model | Source | Grain | Status |
|---|---|---|---|
| `stg_inep_graduacao` | INEP Census | course × IES × municipality × year | ✅ Loaded |
| `stg_inse_escola` | INSE | school × year | ✅ Loaded |
| `stg_ideb_escola` | IDEB | school × year | ✅ Loaded |
| `stg_inep_formandos_ensinomedio` | High school graduates | school × municipality × year | ✅ Loaded |
| `stg_rais_vinculos_municipio` | RAIS employment | municipality × sector × CNAE × year | ✅ Loaded (CNAE sparse) |
| `stg_munic_socio_educ` | IBGE socio-economic | municipality × year | ✅ Loaded |

## Dashboard data flow

1. **Filter:** User selects (UF, municipality, product, tuition % income, CEP)
2. **Renda mínima:** `tuition / (% income / 100)`
3. **API call:** `POST /api/analise` → 7 BigQuery queries in `queries.py`
4. **Frontend render:** Blocks 1–6 populate with tables + KPI strip
5. **Block 7 LLM:** User clicks "⚡ Gerar análise" → `POST /api/analise-llm` + Claude API
6. **Narrative:** 4 paragraphs on market sizing, sector strategy, prospecting, risks

## Important: BigQuery parameter types

The `queries.py::_run()` function auto-detects parameter types:
- `float` → `FLOAT64` (for salary comparisons)
- `int` → `INT64`
- `str` → `STRING`

This is critical for comparisons like `salario_medio_reais >= @renda_min`.

## BigQuery notes

- Source tables may have schema changes in BigQuery (e.g., new columns). Check `sources.yml`.
- RAIS `cnae_2` field is 99% null in current dataset — dashboard still works (subsetor sufficient).
- `profiles.yml` uses OAuth — run `gcloud auth application-default login` if auth fails.

## Dashboard setup checklist

- [ ] `pip install -r dashboard/requirements.txt`
- [ ] Create `dashboard/.env` with `ANTHROPIC_API_KEY=sk-ant-...`
- [ ] `cd dashboard && uvicorn app:app --reload`
- [ ] Test with Campinas (SP, `id_municipio=3509007`)
- [ ] Verify all 7 blocks load + Block 7 LLM works

## Analytics AI Garden integration

This repo is a Sentinel for `C:\meu-digital-garden`. When a milestone is reached, run `/done`.

The `/done` command will:
1. Analyze `git diff HEAD` to capture what changed
2. Extract a Technical Achievement (the "how") and a Managerial Perspective (the "why")
3. Auto-assign a category: `MLOps` for dbt/pipeline, `Data Architecture` for schema/star schema, `GenAI` for Claude integration
4. Export a draft `.md` to `C:\meu-digital-garden\src\content\drafts\`

Review the draft, then move it to `C:\meu-digital-garden\src\content\garden\` to publish.
