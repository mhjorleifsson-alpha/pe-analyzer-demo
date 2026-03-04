# PE Deal Analyzer — Design Document

**Date:** 2026-03-03
**Status:** Validated

---

## Overview

A stateless private equity deal sourcing agent. Users upload one or more deal documents (CIM, teaser, financials), the system classifies the deal type, extracts structured metrics, and displays results in a professional SvelteKit UI. No persistence — each analysis is self-contained.

---

## Architecture

```
┌─────────────────────────────────────┐
│         SvelteKit Frontend          │
│  File dropzone → Progress → Results │
└──────────────┬──────────────────────┘
               │ multipart/form-data (1..N files)
┌──────────────▼──────────────────────┐
│         FastAPI Backend             │
│  POST /analyze                      │
│  Document extraction (markitdown)   │
│  pydantic-ai agent pipeline         │
└──────────────┬──────────────────────┘
               │ LLM API calls
┌──────────────▼──────────────────────┐
│  Configurable LLM Provider (.env)   │
│  Claude | OpenAI | Ollama | compat. │
└─────────────────────────────────────┘
```

---

## Document Extraction

All uploaded files are converted to unified markdown via `markitdown[all]`:

- Supported: PDF, DOCX, XLSX, PPTX, images, HTML, CSV
- Fallback: if a PDF yields < threshold characters, retry with `pymupdf4llm` (handles scanned/image-based PDFs)
- All file outputs are concatenated into a single markdown string fed to the agent pipeline

---

## Provider Configuration

```env
LLM_PROVIDER=anthropic          # anthropic | openai | ollama | openai-compatible
LLM_MODEL=claude-sonnet-4-6
LLM_BASE_URL=                   # required for ollama / openai-compatible only
LLM_API_KEY=sk-...
```

Provider and model are loaded at startup via `config.py`. The pydantic-ai agent is instantiated once from these env vars.

---

## Agent Pipeline

Three pydantic-ai structured output calls:

```
markdown text
    ├──→ [Vitals Agent]       → CompanyVitals
    └──→ [Classifier Agent]   → DealClassification
                                      │
                               ┌──────▼──────┐
                               │ Metrics     │
                               │ Extractor   │ (gated on category)
                               └──────┬──────┘
                                      │
                               BuyoutMetrics | GrowthMetrics | MinorityMetrics
```

Vitals and Classifier run in parallel. Metrics extraction is gated on the classification result to target the correct schema.

---

## Data Models

### CompanyVitals

```python
class CompanyVitals(BaseModel):
    name: str | None
    industry: str | None
    sector: str | None
    geography: str | None        # country / region
    founding_year: int | None
    description: str | None      # 1–2 sentence summary
```

### DealClassification

```python
class DealClassification(BaseModel):
    category: Literal["buyout", "growth", "minority"]
    confidence: float            # 0.0–1.0
    reasoning: str               # brief justification shown in UI
```

### Metrics Models

Metric values are `str | None` — extracted as-found in the document (e.g. `"€12.4M"`, `"~45%"`) without unit normalisation to avoid hallucinated precision.

```python
class BuyoutMetrics(BaseModel):
    revenue: str | None
    ebitda: str | None
    ebitda_margin: str | None
    revenue_growth_rate: str | None
    net_debt: str | None
    leverage_ratio: str | None   # net debt / EBITDA

class GrowthMetrics(BaseModel):
    revenue: str | None
    arr: str | None
    mrr: str | None
    revenue_growth_rate: str | None
    gross_margin: str | None
    net_revenue_retention: str | None
    debt_levels: str | None

class MinorityMetrics(BaseModel):
    revenue: str | None
    ebitda: str | None
    arr: str | None              # if SaaS
    revenue_growth_rate: str | None
    ebitda_margin: str | None
    gross_margin: str | None
    debt_levels: str | None
```

### Unified Output

```python
class DealAnalysis(BaseModel):
    vitals: CompanyVitals
    classification: DealClassification
    metrics: BuyoutMetrics | GrowthMetrics | MinorityMetrics
```

---

## API

| Endpoint   | Method | Description                                      |
| ---------- | ------ | ------------------------------------------------ |
| `/analyze` | POST   | multipart/form-data, returns `DealAnalysis` JSON |
| `/health`  | GET    | confirms provider config is reachable            |

Progress streamed to frontend via SSE during analysis.

---

## Project Structure

```
pe_deal_analysis/
├── backend/
│   ├── main.py              # FastAPI app + SSE streaming
│   ├── agents.py            # pydantic-ai agents (vitals, classifier, metrics)
│   ├── models.py            # Pydantic schemas
│   ├── extraction.py        # markitdown pipeline + pymupdf4llm fallback
│   └── config.py            # .env loading via pydantic-settings
├── frontend/                # SvelteKit app
│   ├── src/
│   │   ├── routes/
│   │   │   └── +page.svelte # single page, three states
│   │   └── lib/
│   │       ├── Dropzone.svelte
│   │       ├── AnalysisProgress.svelte
│   │       ├── VitalsCard.svelte
│   │       ├── ClassificationBadge.svelte
│   │       └── MetricsTable.svelte
│   └── package.json
├── .env
└── pyproject.toml
```

---

## Frontend

**Single-page SvelteKit app, three states:**

1. **Idle** — multi-file dropzone (PDF, DOCX, XLSX, PPTX), Analyze button
2. **Analyzing** — SSE-driven step progress (Extracting → Classifying → Extracting metrics)
3. **Results** — Vitals card + Classification badge with confidence bar + Metrics table + Copy JSON button + Analyze Another Deal button

**Stack:** SvelteKit + Tailwind CSS + shadcn-svelte

Null metric values render as `—`, not empty cells.

---

## Key Design Decisions

| Decision            | Choice                                   | Rationale                                                             |
| ------------------- | ---------------------------------------- | --------------------------------------------------------------------- |
| Document extraction | `markitdown[all]` + pymupdf4llm fallback | Single pipeline, handles all formats including Excel financial tables |
| Metric value types  | `str \| None`                            | Preserves source formatting, avoids hallucinated precision            |
| Agent structure     | 3 separate agents                        | Separation of concerns, independently testable and tunable            |
| Parallelism         | Vitals + Classifier in parallel          | Reduces latency; metrics gated on classification                      |
| Progress UX         | SSE streaming                            | Real-time feedback without polling                                    |
| Persistence         | None                                     | Stateless by design — no database required                            |
