# edu-expansion-intelligence

> **FGV Market Intelligence Dashboard** — Real-time analysis for educational expansion strategy

Interactive web dashboard analyzing municipality opportunity for MBA & postgraduate programs. Combines institutional data (RAIS employment, INEP education, IBGE socioeconomic) with Claude API for executive insights.

Capstone project (TCC) — MBA in AI & Analytics, FGV (2026).

---

## Architecture

```
Raw Data (INEP, RAIS, IBGE, IDEB, INSE)
              ↓
     GCP · BigQuery (raw datasets)
              ↓
     dbt (staging → star schema: dimensions + facts)
              ↓
     FastAPI backend + Claude API
              ↓
     Interactive web dashboard (7 blocks)
              ↓
  Actionable market intelligence
```

---

## Pipeline status

| Stage | Description | Status |
|-------|-------------|--------|
| P1 – Foundation | GCP project, data lake | ✅ Complete |
| P2 – Raw ingestion | INEP, RAIS, IBGE loaded into BigQuery | ✅ Complete |
| P3 – dbt staging | 6 staging views + data quality tests | ✅ Complete |
| P4 – Star schema | Dimensions + Facts tables (market intelligence) | ✅ Complete |
| P5 – Web dashboard | FastAPI + HTML/JS + 7 analytics blocks + Claude | ✅ **Live** |
| P6 – ML clustering | Vertex AI unsupervised clustering (deferred) | ⏳ Planned |

---

## Data sources

| Source | Description | Dashboard blocks |
|--------|-------------|---|
| **RAIS** | Formal employment by municipality, sector, CNAE | Blocks 2, 3 |
| **IBGE** | Municipal socioeconomic indicators (HDI, income, Gini) | Block 1 |
| **INEP Census** | Higher education institutions, graduates, areas | Blocks 5, 7 |
| **Receita Federal (CNPJ)** | Company registry, capital, contact | Block 4 |
| **INSE** | Socioeconomic level of schools | (Feature store) |
| **IDEB** | School performance index | (Feature store) |

---

## Repository structure

```
edu-expansion-intelligence/
├── dashboard/           # FastAPI app + index.html
│   ├── app.py          # FastAPI endpoints (/api/ufs, /api/analise, /api/analise-llm)
│   ├── queries.py      # BigQuery query builders (7 blocks)
│   ├── index.html      # Frontend (Alpine.js, Plotly, Leaflet)
│   └── requirements.txt # Dependencies
├── models/              # dbt models
│   ├── staging/        # 6 views (stg_*)
│   ├── dimensions/     # Reference tables (dim_municipio)
│   ├── facts/          # Aggregated facts (fct_empregos, fct_empresas, etc)
│   └── sources.yml     # Data source definitions
├── data/               # Seeds (reference data)
├── tests/              # dbt data quality tests
├── dbt_project.yml     # dbt configuration
└── profiles.yml        # BigQuery connection (OAuth)
```

---

## Dashboard: 7 Analytics Blocks

| Block | Data | Insight |
|-------|------|---------|
| **1 – Perfil socioeconômico** | IBGE + HDI | City vs state development |
| **2 – Mercado de trabalho** | RAIS (2022) | Eligible salary earners by role + sector |
| **3 – Densidade empresarial** | RAIS + establishments | Sector concentration (corporate vs individual) |
| **4 – Empresas-alvo** | CNPJ + geolocation | Prospecting list by capital social or distance |
| **5 – Formandos por IES** | INEP Census | University pipeline by area of study |
| **6 – Score (0–10)** | Composite (4 dimensions) | Market attractiveness rank |
| **7 – Análise IA** | Claude API | Executive narrative (4 paragraphs) |

---

## Tech stack

**Cloud & Data:** `GCP` `BigQuery` `dbt` `Cloud Run` (planned)

**Backend:** `FastAPI` (Python 3.11+)

**Frontend:** `HTML5` `Alpine.js` `Plotly.js` `Leaflet.js`

**GenAI:** `Claude API` (Anthropic) for narrative generation

**Geospatial:** `geopy` (CEP → coordinates), `haversine` distance (proximity to campus)

**Language:** `Python 3.11+` `SQL` `JavaScript`

---

## Setup & Run

### Prerequisites
```bash
git clone https://github.com/gabifgv/edu-expansion-intelligence.git
cd edu-expansion-intelligence

# Set up GCP auth
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"
# or run: gcloud auth application-default login
```

### Run dbt (populate BigQuery)
```bash
dbt run --select staging dimensions facts
dbt test
```

### Run dashboard locally
```bash
cd dashboard

# Install dependencies
pip install -r requirements.txt

# Create .env with your Anthropic API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# Start server
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Open http://localhost:8000
```

### Test with Campinas
1. **State:** SP (São Paulo)
2. **City:** Campinas (`id_municipio=3509007`)
3. **Product:** MBA or Pós-graduação
4. **Tuition:** 1200 (R$/mês)
5. **% Income:** 9% (default)
6. **Click:** "Analisar mercado →"
7. **Block 7:** Click "⚡ Gerar análise de mercado" for Claude narrative

---

## Key features

✅ **Real-time market analysis** — Query BigQuery live, no batch delay  
✅ **7-dimensional intelligence** — Socioeconomic + employment + education + corporate + AI narratives  
✅ **Geospatial proximity** — Filter companies by distance to FGV campus  
✅ **Executive narratives** — Claude API generates 4-paragraph strategic insights  
✅ **Interactive UI** — Sort, filter, search all tables; responsive design  
✅ **Data quality** — dbt tests for staging models; CNAE sparse but subsetor complete  

---

## Known data issues

| Field | Status | Impact |
|-------|--------|--------|
| RAIS `cnae_2` | 99% null (RAIS source) | Dashboard works; subsetor identifies sector |
| IES geocoding | 100% match via `co_ies` seed | School proximity accurate |
| Company CEP→coords | Geopy + basedosdados CEP directory | ~95% coverage |

---

## Next steps

- [ ] Deploy to Cloud Run (add Dockerfile)
- [ ] Connect Looker Studio for RAIS/INEP dashboards
- [ ] Vertex AI clustering pipeline (P6 — deferred)
- [ ] Fine-tune Claude prompt for sector-specific narratives
- [ ] A/B test portfolio recommendations

---

## Author

**Gabriella Pinheiro** — Data Intelligence Manager at FGV  
[LinkedIn](https://www.linkedin.com/in/gabriella-pinheiro-msc/) · [GitHub](https://github.com/gabifgv)
