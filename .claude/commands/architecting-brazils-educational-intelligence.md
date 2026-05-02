---
title: "Architecting Brazil's Educational Intelligence: A dbt + BigQuery + Vertex AI Pipeline for Strategic Campus Expansion"
date: 2026-04-21
category: "Data Architecture"
keyword: "DataMart"
flower_type: "coral"
id: "0002"
author: "Gabriella Pinheiro"
excerpt: "How I applied medallion architecture principles and economic theory to build a municipality-level intelligence pipeline that helps FGV identify its next campus locations."
---

## The Problem No Spreadsheet Can Solve

Brazil has 5,570 municipalities. Deciding where a premier institution like FGV should expand its physical campus presence is not a marketing question — it is a **resource allocation problem** with deep economic and social dimensions. Which municipalities have the latent demand for higher education but remain structurally underserved? Where does the gap between formal employment growth and higher education supply represent a genuine market opportunity?

These are the questions my MBA capstone TCC at FGV attempts to answer. And answering them properly required building a data architecture from the ground up — not a dashboard, not a report, but a **production-grade intelligence pipeline** capable of synthesizing six independent Brazilian public datasets into a single analytical surface.

This is the architectural story of `edu-expansion-intelligence`.

---

## Why Architecture Before Models

There is a temptation in data science to go straight to the model. My MSc in Economics at UFF trained me to resist that impulse. An economist's first instinct is to interrogate the **data generating process** — how was this measured, by whom, at what grain, with what coverage gaps? Before any clustering algorithm runs on Vertex AI, the data must be trusted. And trust requires architecture.

At FGV, I have spent nearly five years designing a medallion architecture (Bronze/Silver/Gold) on Microsoft Fabric for our Marketing Analytics division. The same principle governs this TCC: **raw data is never the source of truth; curated, validated, modeled data is**.

The pipeline follows a strict layered pattern:

```
Public Sources (INEP, RAIS, Atlas ADH, IDEB, INSE, Censo Escolar)
        ↓  BigQuery raw dataset
dbt Staging Layer — 6 views
        ↓
dbt Marts Layer — mart_municipio_perfil
        ↓
Vertex AI — unsupervised K-Means clustering
        ↓
Gemini + LangChain — natural language strategic narratives
```

The grain is **municipality × year**, using the IBGE 7-digit `id_municipio` as the universal join key across all six sources.

---

## The Six Staging Models: Economics in Code

Each of the six staging models (`stg_*`) is deliberately single-source: one staging model reads from exactly one raw table. No joins. No business logic. Only **three operations are permitted at the staging layer**: rename, cast, and classify.

This is not aesthetic minimalism — it is **data lineage hygiene**. When a mart breaks in production, you want to know immediately whether the issue is in the source, the staging transform, or the business logic. Mixing those concerns collapses your debugging surface.

The six sources bring their own economic reasoning:

- **`stg_inep_graduacao`** — Higher education supply by course, institution, and modality (Presencial vs. EAD). The presencial/EAD split is not cosmetic: it tells you whether a market needs a physical campus or is already served by distance learning.
- **`stg_inse_escola`** — Socioeconomic index per school (8-tier scale, I through VIII). This is the **demand-side signal**: municipalities with high concentrations of INSE VII–VIII students have populations capable of financing higher education.
- **`stg_ideb_escola`** — Academic quality of high school education. From my time at IDados, working with INEP and Censo Escolar for public policy clients, I learned that IDEB is a composite index (SAEB proficiency × graduation rate) — not just a test score. A municipality with IDEB ≥ 6.0 produces students academically prepared for university.
- **`stg_inep_formandos_ensinomedio`** — Annual high school graduates, the direct **enrollment funnel proxy**. Stream codes 27, 32, and 37 identify the propedêutic track feeding university applications.
- **`stg_rais_vinculos_municipio`** — Formal labor market demand. Salary growth in a municipality signals ROI on education: if formal employment pays competitively, higher education has a demonstrated economic return.
- **`stg_munic_socio_educ`** — Municipal HDI, Gini coefficient, per capita income, and poverty headcount. The **economic development triad** that anchors every other metric in structural context.

## The Classification Design: Encoding Economic Judgment

At the staging layer, continuous variables are classified into ordinal tiers using CASE expressions. For `idhm`, the five bands (Muito Alto ≥ 0.900 down to Muito Baixo < 0.500) directly mirror the PNUD Human Development classification. For `ideb`, the four performance bands (Excelente/Alto/Médio/Baixo) encode the policy consensus on acceptable school quality thresholds.

These are not arbitrary buckets. They are **institutionally validated thresholds** from the Brazilian public statistics ecosystem — the same thresholds used in PNUD reports and MEC policy documents. By encoding them in dbt, they become reusable, testable, and version-controlled — not buried in someone's Excel formula.

The dbt test suite enforces this at schema validation: 20+ generic tests using `accepted_values` with `arguments:` nesting (dbt 1.11 syntax) ensure that no rogue classification leaks into the mart layer.

---

## The Road to `mart_municipio_perfil`

The central ML feature table, currently in design, will aggregate all six staging models to municipality grain. The intended feature vector includes: `idhm`, `renda_per_capita`, `populacao_18_24`, `taxa_freq_bruta_superior`, `salario_medio_reais`, `total_matriculas_ies`, `ideb_medio_municipio`, `pct_escolas_inse_alto`, and `indice_gini`.

From an economics standpoint, this feature set captures three orthogonal dimensions of municipal readiness for higher education investment:

1. **Human capital stock** — IDHM subcodes, IDEB, INSE classification
2. **Market demand potential** — youth cohort size, higher-ed enrollment rates, graduate pipeline
3. **Economic capacity and return** — per capita income, Gini inequality, formal employment salaries

The Vertex AI K-Means clustering on this feature space will produce a **taxonomy of municipalities** — not a ranking, but a strategic segmentation. An economist's instinct is to resist reducing complex regional disparities to a single score. Clustering respects that complexity.

---

## The Gemini Layer: From Clusters to C-Level Language

The final pipeline stage uses LangChain + Gemini to generate natural language strategic narratives for each identified cluster. This is where the RAG architecture principles I applied in FGV's Marketing Analytics division find their academic expression.

The LLM does not replace the analyst. It **translates** — converting a 9-dimensional feature vector into a narrative a university rector can act on: *"Cluster 3 municipalities show high youth population density, above-median IDEB scores, and formal employment salary growth of 12% YoY — but only 18% higher education enrollment rate. This represents the highest-priority expansion opportunity in the Southern region."*

This is the pipeline's ambition: bridging econometric rigor and executive communication.

---

## What This Project Taught Me About Scale

Building this pipeline taught me that **data architecture is a form of institutional knowledge management**. The six sources I integrated for this TCC are the same sources Brazilian public administrators use to monitor educational inequality. By modularizing them in dbt with clear lineage and schema validation, I am not just building a model — I am building infrastructure that could be reused by any researcher studying the same problem.

That is what distinguishes architecture from analysis. Analysis answers a question. Architecture scales the capacity to answer questions.

The garden continues.
