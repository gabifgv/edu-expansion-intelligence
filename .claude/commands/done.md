Analyze the current git diff and generate a draft post for the Analytics AI Garden.

This repo is the MBA capstone: MLOps + GenAI pipeline for educational market intelligence in Brazil (dbt → BigQuery → Vertex AI → Gemini). Context: clustering municipalities by socioeconomic profile for FGV campus expansion decisions.

Steps:
1. Run `git diff HEAD --stat` then `git diff HEAD` to capture all changes.
2. Extract:
   - **Technical Achievement**: specific dbt models changed, SQL logic added, BigQuery queries optimized, Vertex AI config updated, or Python analysis produced
   - **Managerial Perspective**: how the change advances the clustering pipeline, improves data quality for strategic decisions, or unblocks a downstream step
3. Assign category:
   - `MLOps` for dbt model changes, pipeline work, Vertex AI, dbt tests
   - `Data Architecture` for schema changes, new sources, mart design, BigQuery optimization
   - `GenAI` for Gemini integration, LangChain chains, prompt engineering
4. Choose a single `keyword` (≤12 chars) representing the core concept (e.g., "Clustering", "dbt", "BigQuery", "Gemini").
5. Save the draft to `C:\meu-digital-garden\src\content\drafts\YYYY-MM-DD-[topic-slug].md` using this structure:

```markdown
---
title: "[Action-oriented title]"
date: YYYY-MM-DD
category: "[GenAI|MLOps|Data Architecture]"
keyword: "[SingleWord]"
id: "DRAFT"
author: "Gabriella Pinheiro"
status: "Draft 🌿"
excerpt: "[One sentence summary of what was achieved]"
---

## Technical Achievement

[Specific: which dbt model, which BigQuery table, which Vertex AI step. Name the files changed. Explain the pattern used.]

## Managerial Perspective

[How this advances the FGV expansion intelligence pipeline. Strategic impact on the municipality clustering or Gemini insight generation.]

## Key Decisions

- [Technical trade-off or architectural choice made]
- [Why this approach over alternatives]

## What's Next

[Next logical step in the pipeline.]
```

Confirm the saved path. Remind Gabriella to review before moving to `C:\meu-digital-garden\src\content\garden\`.
