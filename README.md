# edu-expansion-intelligence

> MLOps + GenAI pipeline for educational market intelligence in Brazil

End-to-end data and AI system that clusters Brazilian municipalities by socioeconomic and educational profile, then uses Generative AI to translate those clusters into actionable, natural-language insights for educational expansion strategy.

Capstone project (TCC) — MBA in AI & Analytics, FGV (2026).

---

## Architecture

```
Raw Data (INEP, RAIS, IBGE, IDEB, INSE)
              ↓
     GCP · BigQuery (raw_staging)
              ↓
     dbt (staging → marts)
              ↓
     Vertex AI · Unsupervised Clustering
              ↓
     Gemini + LangChain Agent
              ↓
  Strategic insights in natural language
```

---

## Pipeline status

| Stage | Description | Status |
|-------|-------------|--------|
| P1 – Foundation | GCP project setup, data lake structure | ✅ Complete |
| P2 – Raw ingestion | INEP, RAIS, IBGE, IDEB loaded into BigQuery | ✅ Complete |
| P3 – dbt staging | 6 staging models, 20+ tests, `raw_staging` dataset | ✅ Complete |
| P4 – Vertex AI MLOps | Unsupervised clustering pipeline | 🔄 In progress |
| P5 – GenAI agent | Gemini + LangChain for natural language output | 🔄 In progress |

---

## Data sources

| Source | Description |
|--------|-------------|
| INEP Census | Higher education institutions and graduates |
| RAIS | Formal employment by municipality |
| IDEB | Basic education quality index |
| INSE | Socioeconomic level of schools |
| IBGE | Municipal socioeconomic indicators |

---

## Repository structure

```
edu-expansion-intelligence/
├── analyses/        # Exploratory and ad-hoc analyses
├── data/            # Seeds and reference data
├── macros/          # dbt reusable macros
├── models/          # dbt staging and mart models
├── tests/           # dbt custom data tests
├── dbt_project.yml  # dbt project configuration
└── profiles.yml     # Connection profiles
```

---

## dbt staging models

| Model | Source |
|-------|--------|
| `stg_inep_graduacao` | INEP higher education graduates |
| `stg_inse_escola` | School socioeconomic index |
| `stg_ideb_escola` | IDEB school performance |
| `stg_inep_formandos_ensinomedio` | High school graduates |
| `stg_rais_vinculos_municipio` | Formal employment by municipality |
| `stg_munic_socio_educ` | Municipal socioeconomic indicators |

---

## Tech stack

**Cloud:** `GCP` `BigQuery` `Vertex AI` `Cloud Run` `Cloud Functions`

**Data Engineering:** `dbt` `BigQuery` `Python`

**MLOps:** `Vertex AI Pipelines` `Model Registry` `Model Monitoring`

**GenAI:** `Gemini Pro` `LangChain` `RAG Architecture`

**Language:** `Python 3.11+` `SQL`

---

## Setup

```bash
git clone https://github.com/gabifgv/edu-expansion-intelligence.git
cd edu-expansion-intelligence

pip install -r requirements.txt

export GOOGLE_APPLICATION_CREDENTIALS="your-key.json"

# Run dbt staging
dbt run --select staging
dbt test --select staging
```

---

## Author

**Gabriella Pinheiro** — Data Intelligence Manager at FGV
[LinkedIn](https://www.linkedin.com/in/gabriella-pinheiro-msc/) · [GitHub](https://github.com/gabifgv)
