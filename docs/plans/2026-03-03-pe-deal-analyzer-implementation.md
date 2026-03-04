# PE Deal Analyzer — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a stateless PE deal sourcing agent — upload documents, get deal classification + structured metrics — with a FastAPI backend (pydantic-ai) and SvelteKit frontend.

**Architecture:** markitdown extracts all uploaded files to markdown, two parallel pydantic-ai agents (vitals + classifier) run first, then a category-specific metrics agent runs based on the classification result. Progress streamed to frontend via SSE over POST.

**Tech Stack:** Python 3.12+, uv, FastAPI, pydantic-ai, markitdown[all], pymupdf4llm, SvelteKit, Tailwind CSS, shadcn-svelte

---

## Task 1: Project Scaffolding

**Files:**

- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `backend/__init__.py`
- Create: `tests/__init__.py`
- Create: `.gitignore`

**Step 1: Initialise uv project**

```bash
cd /Users/mikeh/Downloads/pe_deal_analysis
uv init --no-workspace
uv python pin 3.12
```

**Step 2: Replace pyproject.toml with full deps**

```toml
[project]
name = "pe-deal-analysis"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic-ai>=0.0.14",
    "pydantic-settings>=2.6.0",
    "markitdown[all]>=0.1.0",
    "pymupdf4llm>=0.0.17",
    "python-multipart>=0.0.9",
    "httpx>=0.27.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 3: Install dependencies**

```bash
uv sync
```

Expected: lock file created, `.venv/` present.

**Step 4: Create directory structure**

```bash
mkdir -p backend tests frontend
touch backend/__init__.py tests/__init__.py
```

**Step 5: Create .env.example**

```bash
cat > .env.example << 'EOF'
# Provider: anthropic | openai | ollama | openai-compatible
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-6
LLM_API_KEY=sk-ant-...
# Only needed for ollama or openai-compatible providers:
LLM_BASE_URL=
EOF
```

**Step 6: Create .gitignore**

```
.venv/
__pycache__/
*.pyc
.env
*.egg-info/
dist/
node_modules/
.svelte-kit/
frontend/build/
```

**Step 7: Copy .env.example to .env and fill in real values**

```bash
cp .env.example .env
# Edit .env with real LLM_PROVIDER, LLM_MODEL, LLM_API_KEY
```

**Step 8: Commit**

```bash
git init
git add pyproject.toml uv.lock .env.example .gitignore backend/__init__.py tests/__init__.py
git commit -m "chore: project scaffolding"
```

---

## Task 2: Config Module

**Files:**

- Create: `backend/config.py`
- Create: `tests/test_config.py`

**Step 1: Write the failing test**

```python
# tests/test_config.py
import os
import pytest
from backend.config import Settings


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_BASE_URL", "")
    s = Settings()
    assert s.llm_provider == "openai"
    assert s.llm_model == "gpt-4o"
    assert s.llm_api_key == "sk-test"
    assert s.llm_base_url == ""


def test_settings_valid_providers(monkeypatch):
    for provider in ["anthropic", "openai", "ollama", "openai-compatible"]:
        monkeypatch.setenv("LLM_PROVIDER", provider)
        monkeypatch.setenv("LLM_MODEL", "some-model")
        monkeypatch.setenv("LLM_API_KEY", "key")
        s = Settings()
        assert s.llm_provider == provider
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_config.py -v
```

Expected: FAIL — `cannot import name 'Settings'`

**Step 3: Implement config.py**

```python
# backend/config.py
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    llm_provider: str = Field(default="anthropic")
    llm_model: str = Field(default="claude-sonnet-4-6")
    llm_api_key: str = Field(default="")
    llm_base_url: str = Field(default="")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_config.py -v
```

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add backend/config.py tests/test_config.py
git commit -m "feat: settings module with pydantic-settings"
```

---

## Task 3: Data Models

**Files:**

- Create: `backend/models.py`
- Create: `tests/test_models.py`

**Step 1: Write the failing test**

```python
# tests/test_models.py
from backend.models import (
    CompanyVitals,
    DealClassification,
    BuyoutMetrics,
    GrowthMetrics,
    MinorityMetrics,
    DealAnalysis,
)


def test_vitals_all_optional():
    v = CompanyVitals()
    assert v.name is None
    assert v.description is None


def test_vitals_with_data():
    v = CompanyVitals(name="Acme Corp", geography="Germany", founding_year=2005)
    assert v.name == "Acme Corp"
    assert v.founding_year == 2005


def test_classification():
    c = DealClassification(category="buyout", confidence=0.92, reasoning="High leverage, mature business")
    assert c.category == "buyout"
    assert 0.0 <= c.confidence <= 1.0


def test_buyout_metrics_all_optional():
    m = BuyoutMetrics()
    assert m.revenue is None
    assert m.leverage_ratio is None


def test_growth_metrics():
    m = GrowthMetrics(arr="€5.2M", revenue_growth_rate="85% YoY")
    assert m.arr == "€5.2M"


def test_minority_metrics():
    m = MinorityMetrics(revenue="€20M", ebitda="€4M")
    assert m.ebitda == "€4M"


def test_deal_analysis_buyout():
    analysis = DealAnalysis(
        vitals=CompanyVitals(name="TestCo"),
        classification=DealClassification(category="buyout", confidence=0.9, reasoning="test"),
        metrics=BuyoutMetrics(revenue="€50M"),
    )
    assert analysis.vitals.name == "TestCo"
    assert analysis.classification.category == "buyout"
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_models.py -v
```

Expected: FAIL — import errors

**Step 3: Implement models.py**

```python
# backend/models.py
from typing import Literal
from pydantic import BaseModel


class CompanyVitals(BaseModel):
    name: str | None = None
    industry: str | None = None
    sector: str | None = None
    geography: str | None = None
    founding_year: int | None = None
    description: str | None = None


class DealClassification(BaseModel):
    category: Literal["buyout", "growth", "minority"]
    confidence: float
    reasoning: str


class BuyoutMetrics(BaseModel):
    revenue: str | None = None
    ebitda: str | None = None
    ebitda_margin: str | None = None
    revenue_growth_rate: str | None = None
    net_debt: str | None = None
    leverage_ratio: str | None = None


class GrowthMetrics(BaseModel):
    revenue: str | None = None
    arr: str | None = None
    mrr: str | None = None
    revenue_growth_rate: str | None = None
    gross_margin: str | None = None
    net_revenue_retention: str | None = None
    debt_levels: str | None = None


class MinorityMetrics(BaseModel):
    revenue: str | None = None
    ebitda: str | None = None
    arr: str | None = None
    revenue_growth_rate: str | None = None
    ebitda_margin: str | None = None
    gross_margin: str | None = None
    debt_levels: str | None = None


class DealAnalysis(BaseModel):
    vitals: CompanyVitals
    classification: DealClassification
    metrics: BuyoutMetrics | GrowthMetrics | MinorityMetrics
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_models.py -v
```

Expected: PASS (8 tests)

**Step 5: Commit**

```bash
git add backend/models.py tests/test_models.py
git commit -m "feat: pydantic data models for deal analysis"
```

---

## Task 4: Document Extraction

**Files:**

- Create: `backend/extraction.py`
- Create: `tests/test_extraction.py`
- Create: `tests/fixtures/sample.txt`

**Step 1: Create a text fixture**

```bash
mkdir -p tests/fixtures
echo "Acme Corp Q4 2024 Revenue: €42.3M EBITDA: €8.1M" > tests/fixtures/sample.txt
```

**Step 2: Write the failing tests**

```python
# tests/test_extraction.py
import pytest
from pathlib import Path
from backend.extraction import extract_to_markdown, MIN_CHAR_THRESHOLD

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_plain_text(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("Hello world financial data Revenue: €10M")
    result = extract_to_markdown(str(f))
    assert "Revenue" in result
    assert len(result) > 10


def test_extract_returns_string(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("Some content")
    result = extract_to_markdown(str(f))
    assert isinstance(result, str)


def test_min_char_threshold_is_defined():
    assert isinstance(MIN_CHAR_THRESHOLD, int)
    assert MIN_CHAR_THRESHOLD > 0


def test_extract_multiple_files_concatenated(tmp_path):
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("Document A content")
    f2.write_text("Document B content")
    from backend.extraction import extract_files_to_markdown
    result = extract_files_to_markdown([str(f1), str(f2)])
    assert "Document A" in result
    assert "Document B" in result
```

**Step 3: Run test to verify it fails**

```bash
uv run pytest tests/test_extraction.py -v
```

Expected: FAIL — import errors

**Step 4: Implement extraction.py**

```python
# backend/extraction.py
import tempfile
import os
from pathlib import Path
from markitdown import MarkItDown

MIN_CHAR_THRESHOLD = 200


def extract_to_markdown(file_path: str) -> str:
    """Convert a single file to markdown via markitdown.
    Falls back to pymupdf4llm for PDFs that yield too little text.
    """
    md = MarkItDown()
    result = md.convert(file_path)
    text = result.text_content or ""

    # Fallback for scanned/image-based PDFs
    if file_path.lower().endswith(".pdf") and len(text.strip()) < MIN_CHAR_THRESHOLD:
        text = _pymupdf_fallback(file_path)

    return text


def _pymupdf_fallback(file_path: str) -> str:
    """Extract PDF text using pymupdf4llm (handles scanned docs)."""
    import pymupdf4llm
    return pymupdf4llm.to_markdown(file_path)


def extract_files_to_markdown(file_paths: list[str]) -> str:
    """Extract and concatenate multiple files into a single markdown string."""
    parts = []
    for path in file_paths:
        text = extract_to_markdown(path)
        if text.strip():
            filename = Path(path).name
            parts.append(f"## Source: {filename}\n\n{text.strip()}")
    return "\n\n---\n\n".join(parts)


async def extract_uploads_to_markdown(files: list) -> str:
    """Accept FastAPI UploadFile objects, save to temp, extract, clean up."""
    temp_paths = []
    try:
        for upload in files:
            suffix = Path(upload.filename or "file").suffix or ".bin"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                content = await upload.read()
                tmp.write(content)
                temp_paths.append(tmp.name)
        return extract_files_to_markdown(temp_paths)
    finally:
        for path in temp_paths:
            try:
                os.unlink(path)
            except OSError:
                pass
```

**Step 5: Run test to verify it passes**

```bash
uv run pytest tests/test_extraction.py -v
```

Expected: PASS (4 tests)

**Step 6: Commit**

```bash
git add backend/extraction.py tests/test_extraction.py tests/fixtures/sample.txt
git commit -m "feat: document extraction pipeline with markitdown + pymupdf fallback"
```

---

## Task 5: pydantic-ai Agents

**Files:**

- Create: `backend/agents.py`
- Create: `tests/test_agents.py`

**Step 1: Write the failing tests**

```python
# tests/test_agents.py
import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock
from backend.models import (
    CompanyVitals, DealClassification, BuyoutMetrics,
    GrowthMetrics, MinorityMetrics, DealAnalysis
)


def test_build_model_anthropic(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_MODEL", "claude-sonnet-4-6")
    monkeypatch.setenv("LLM_API_KEY", "sk-ant-test")
    monkeypatch.setenv("LLM_BASE_URL", "")
    # Reimport after env change
    import importlib
    import backend.config
    importlib.reload(backend.config)
    from backend.agents import build_model
    model = build_model()
    assert model is not None


def test_build_model_openai(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_BASE_URL", "")
    import importlib
    import backend.config
    importlib.reload(backend.config)
    from backend.agents import build_model
    model = build_model()
    assert model is not None


@pytest.mark.asyncio
async def test_run_pipeline_returns_deal_analysis(monkeypatch):
    """Test pipeline with pydantic-ai TestModel to avoid real LLM calls."""
    from pydantic_ai.models.test import TestModel
    from backend.agents import run_pipeline

    # Patch the agents to use TestModel
    vitals_mock = CompanyVitals(name="TestCo", geography="France")
    classification_mock = DealClassification(
        category="buyout", confidence=0.88, reasoning="Mature profitable business"
    )
    metrics_mock = BuyoutMetrics(revenue="€42M", ebitda="€8M")

    with patch("backend.agents.vitals_agent") as mock_v, \
         patch("backend.agents.classifier_agent") as mock_c, \
         patch("backend.agents.buyout_metrics_agent") as mock_m:

        mock_v.run = AsyncMock(return_value=MagicMock(data=vitals_mock))
        mock_c.run = AsyncMock(return_value=MagicMock(data=classification_mock))
        mock_m.run = AsyncMock(return_value=MagicMock(data=metrics_mock))

        result = await run_pipeline("Some deal markdown text")

    assert isinstance(result, DealAnalysis)
    assert result.vitals.name == "TestCo"
    assert result.classification.category == "buyout"
    assert isinstance(result.metrics, BuyoutMetrics)
    assert result.metrics.revenue == "€42M"
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_agents.py -v
```

Expected: FAIL — import errors

**Step 3: Implement agents.py**

```python
# backend/agents.py
import asyncio
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIModel
from backend.config import get_settings
from backend.models import (
    CompanyVitals,
    DealClassification,
    BuyoutMetrics,
    GrowthMetrics,
    MinorityMetrics,
    DealAnalysis,
)

_VITALS_SYSTEM = """You are a financial analyst assistant. Extract basic company profile information
from the provided deal document (CIM, teaser, or financial model). Return only what is explicitly
stated in the document — do not infer or fabricate values."""

_CLASSIFIER_SYSTEM = """You are a private equity deal classification expert. Classify the deal
into exactly one of three categories:
- buyout: acquiring majority/full control of a mature, profitable business
- growth: minority or majority investment in a high-growth, typically loss-making or early-profit company
- minority: taking a minority stake in an established business without control

Base your classification on deal structure, financial profile, and language in the document.
Provide a confidence score (0.0–1.0) and brief reasoning."""

_BUYOUT_METRICS_SYSTEM = """You are a private equity financial analyst. Extract buyout deal metrics
from the document. Return values exactly as they appear (e.g. '€42.3M', '~19%').
Return null for any metric not found in the document. Do not estimate or interpolate."""

_GROWTH_METRICS_SYSTEM = """You are a venture/growth equity analyst. Extract growth deal metrics
from the document. Focus on ARR/MRR, growth rates, and retention. Return values exactly as they
appear. Return null for any metric not found. Do not estimate or interpolate."""

_MINORITY_METRICS_SYSTEM = """You are a private equity analyst. Extract minority deal metrics
from the document. Include both SaaS metrics (ARR if applicable) and traditional metrics (EBITDA).
Return values exactly as they appear. Return null for any metric not found."""


def build_model():
    """Build a pydantic-ai model instance from env configuration."""
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "anthropic":
        return AnthropicModel(settings.llm_model, api_key=settings.llm_api_key)

    if provider in ("openai", "ollama", "openai-compatible"):
        kwargs = {"api_key": settings.llm_api_key or "ollama"}
        if settings.llm_base_url:
            kwargs["base_url"] = settings.llm_base_url
        return OpenAIModel(settings.llm_model, **kwargs)

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider!r}")


_model = build_model()

vitals_agent = Agent(
    model=_model,
    result_type=CompanyVitals,
    system_prompt=_VITALS_SYSTEM,
)

classifier_agent = Agent(
    model=_model,
    result_type=DealClassification,
    system_prompt=_CLASSIFIER_SYSTEM,
)

buyout_metrics_agent = Agent(
    model=_model,
    result_type=BuyoutMetrics,
    system_prompt=_BUYOUT_METRICS_SYSTEM,
)

growth_metrics_agent = Agent(
    model=_model,
    result_type=GrowthMetrics,
    system_prompt=_GROWTH_METRICS_SYSTEM,
)

minority_metrics_agent = Agent(
    model=_model,
    result_type=MinorityMetrics,
    system_prompt=_MINORITY_METRICS_SYSTEM,
)


async def run_pipeline(markdown: str) -> DealAnalysis:
    """Run the full agent pipeline: vitals + classifier in parallel, then metrics."""
    vitals_result, classifier_result = await asyncio.gather(
        vitals_agent.run(markdown),
        classifier_agent.run(markdown),
    )

    vitals = vitals_result.data
    classification = classifier_result.data

    metrics_prompt = f"Deal category: {classification.category}\n\n{markdown}"

    match classification.category:
        case "buyout":
            metrics_result = await buyout_metrics_agent.run(metrics_prompt)
        case "growth":
            metrics_result = await growth_metrics_agent.run(metrics_prompt)
        case "minority":
            metrics_result = await minority_metrics_agent.run(metrics_prompt)
        case _:
            raise ValueError(f"Unknown category: {classification.category}")

    return DealAnalysis(
        vitals=vitals,
        classification=classification,
        metrics=metrics_result.data,
    )
```

**Step 4: Verify import**

```bash
uv run python -c "from backend.agents import run_pipeline; print('OK')"
```

Expected: `OK`

**Step 5: Run tests**

```bash
uv run pytest tests/test_agents.py -v
```

Expected: PASS (3 tests)

**Step 6: Commit**

```bash
git add backend/agents.py tests/test_agents.py
git commit -m "feat: pydantic-ai agents for vitals, classification, and metrics extraction"
```

---

## Task 6: FastAPI Application

**Files:**

- Create: `backend/main.py`
- Create: `tests/test_main.py`

**Step 1: Write the failing tests**

```python
# tests/test_main.py
import json
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.models import (
    CompanyVitals, DealClassification, BuyoutMetrics, DealAnalysis
)


@pytest.fixture
def mock_analysis():
    return DealAnalysis(
        vitals=CompanyVitals(name="Acme Corp", geography="Germany"),
        classification=DealClassification(
            category="buyout", confidence=0.91, reasoning="Mature profitable"
        ),
        metrics=BuyoutMetrics(revenue="€42M", ebitda="€8M"),
    )


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "provider" in data


@pytest.mark.asyncio
async def test_analyze_endpoint_streams_sse(mock_analysis):
    from io import BytesIO
    fake_file_content = b"Revenue EUR 42M EBITDA EUR 8M leveraged buyout"

    with patch("backend.main.extract_uploads_to_markdown", new_callable=AsyncMock) as mock_extract, \
         patch("backend.main.run_pipeline", new_callable=AsyncMock) as mock_pipeline:

        mock_extract.return_value = "Revenue EUR 42M"
        mock_pipeline.return_value = mock_analysis

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/analyze",
                files={"files": ("test.txt", BytesIO(fake_file_content), "text/plain")},
            )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    # Parse SSE events from response body
    body = response.text
    events = [line for line in body.split("\n") if line.startswith("data:")]
    assert len(events) >= 4  # extracting, classifying, extracting_metrics, result

    # Last event should be the result
    last_event = json.loads(events[-1].removeprefix("data: "))
    assert last_event["type"] == "result"
    assert last_event["data"]["vitals"]["name"] == "Acme Corp"
    assert last_event["data"]["classification"]["category"] == "buyout"
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_main.py -v
```

Expected: FAIL — import errors

**Step 3: Implement main.py**

```python
# backend/main.py
import json
import asyncio
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from backend.config import get_settings
from backend.extraction import extract_uploads_to_markdown
from backend.agents import run_pipeline

app = FastAPI(title="PE Deal Analyzer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse(event_data: dict) -> str:
    return f"data: {json.dumps(event_data)}\n\n"


@app.get("/health")
async def health():
    settings = get_settings()
    return {"status": "ok", "provider": settings.llm_provider, "model": settings.llm_model}


@app.post("/analyze")
async def analyze(files: list[UploadFile] = File(...)):
    async def event_stream():
        try:
            yield _sse({"type": "progress", "step": "extracting", "message": "Extracting documents..."})
            markdown = await extract_uploads_to_markdown(files)

            yield _sse({"type": "progress", "step": "classifying", "message": "Classifying deal..."})
            # Small yield to flush the event before blocking on LLM calls
            await asyncio.sleep(0)

            # Vitals + classifier run in parallel inside run_pipeline
            # We emit "extracting_metrics" after classification completes
            # To do this we run vitals+classifier first, then emit, then metrics
            from backend.agents import (
                vitals_agent, classifier_agent,
                buyout_metrics_agent, growth_metrics_agent, minority_metrics_agent
            )
            from backend.models import DealAnalysis

            vitals_result, classifier_result = await asyncio.gather(
                vitals_agent.run(markdown),
                classifier_agent.run(markdown),
            )
            vitals = vitals_result.data
            classification = classifier_result.data

            yield _sse({"type": "progress", "step": "extracting_metrics", "message": "Extracting metrics..."})
            await asyncio.sleep(0)

            metrics_prompt = f"Deal category: {classification.category}\n\n{markdown}"
            match classification.category:
                case "buyout":
                    metrics_result = await buyout_metrics_agent.run(metrics_prompt)
                case "growth":
                    metrics_result = await growth_metrics_agent.run(metrics_prompt)
                case "minority":
                    metrics_result = await minority_metrics_agent.run(metrics_prompt)
                case _:
                    raise ValueError(f"Unknown category: {classification.category!r}")

            result = DealAnalysis(
                vitals=vitals,
                classification=classification,
                metrics=metrics_result.data,
            )

            yield _sse({"type": "result", "data": result.model_dump()})

        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

**Step 4: Verify import**

```bash
uv run python -c "from backend.main import app; print('OK')"
```

Expected: `OK`

**Step 5: Run all backend tests**

```bash
uv run pytest tests/ -v
```

Expected: All tests PASS

**Step 6: Smoke test the server manually**

```bash
uv run uvicorn backend.main:app --reload --port 8000
# In another terminal:
curl http://localhost:8000/health
```

Expected: `{"status":"ok","provider":"...","model":"..."}`

**Step 7: Commit**

```bash
git add backend/main.py tests/test_main.py
git commit -m "feat: FastAPI app with SSE streaming analyze endpoint"
```

---

## Task 7: SvelteKit Frontend Scaffold

**Files:**

- Create: `frontend/` (SvelteKit project)
- Modify: `frontend/vite.config.ts` (add backend proxy)

**Step 1: Scaffold SvelteKit project**

```bash
cd /Users/mikeh/Downloads/pe_deal_analysis
npm create svelte@latest frontend
# Select: Skeleton project, TypeScript, no additional options
cd frontend
npm install
```

**Step 2: Add Tailwind CSS**

```bash
npm install -D tailwindcss @tailwindcss/vite
```

Create `frontend/src/app.css`:

```css
@import "tailwindcss";
```

Add to `frontend/src/routes/+layout.svelte`:

```svelte
<script>
  import '../app.css';
</script>
<slot />
```

Update `frontend/vite.config.ts`:

```typescript
import { sveltekit } from "@sveltejs/kit/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  server: {
    proxy: {
      "/analyze": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
```

**Step 3: Add shadcn-svelte**

```bash
npx shadcn-svelte@latest init
# Accept defaults: use TypeScript, default style, default base color
npx shadcn-svelte@latest add card badge progress separator
```

**Step 4: Verify dev server starts**

```bash
npm run dev
```

Expected: Server starts at http://localhost:5173 with no errors.

**Step 5: Commit**

```bash
cd /Users/mikeh/Downloads/pe_deal_analysis
git add frontend/
git commit -m "chore: SvelteKit scaffold with Tailwind and shadcn-svelte"
```

---

## Task 8: Dropzone Component

**Files:**

- Create: `frontend/src/lib/Dropzone.svelte`

**Step 1: Implement Dropzone.svelte**

```svelte
<!-- frontend/src/lib/Dropzone.svelte -->
<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher<{ files: File[] }>();

  let dragging = false;
  let inputEl: HTMLInputElement;

  const ACCEPTED = '.pdf,.docx,.xlsx,.pptx';

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    dragging = false;
    const files = Array.from(e.dataTransfer?.files ?? []);
    if (files.length) dispatch('files', files);
  }

  function handleChange(e: Event) {
    const input = e.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    if (files.length) dispatch('files', files);
  }
</script>

<button
  class="w-full rounded-xl border-2 border-dashed p-12 text-center transition-colors
         {dragging ? 'border-blue-500 bg-blue-50' : 'border-zinc-300 hover:border-zinc-400 hover:bg-zinc-50'}"
  on:dragover|preventDefault={() => (dragging = true)}
  on:dragleave={() => (dragging = false)}
  on:drop={handleDrop}
  on:click={() => inputEl.click()}
  type="button"
>
  <input
    bind:this={inputEl}
    type="file"
    multiple
    accept={ACCEPTED}
    class="hidden"
    on:change={handleChange}
  />
  <div class="pointer-events-none space-y-2">
    <p class="text-lg font-medium text-zinc-700">Drop files here or click to upload</p>
    <p class="text-sm text-zinc-400">PDF · DOCX · XLSX · PPTX · Multiple files supported</p>
  </div>
</button>
```

**Step 2: Verify component exists and dev server still starts**

```bash
cd frontend && npm run dev &
sleep 3 && curl -s http://localhost:5173 | grep -q "html" && echo "OK" || echo "FAIL"
kill %1
```

Expected: `OK`

**Step 3: Commit**

```bash
cd /Users/mikeh/Downloads/pe_deal_analysis
git add frontend/src/lib/Dropzone.svelte
git commit -m "feat: file dropzone component with drag-and-drop"
```

---

## Task 9: AnalysisProgress Component

**Files:**

- Create: `frontend/src/lib/AnalysisProgress.svelte`

**Step 1: Implement AnalysisProgress.svelte**

```svelte
<!-- frontend/src/lib/AnalysisProgress.svelte -->
<script lang="ts">
  export let currentStep: string = '';

  const steps = [
    { id: 'extracting', label: 'Extracting documents' },
    { id: 'classifying', label: 'Classifying deal' },
    { id: 'extracting_metrics', label: 'Extracting metrics' },
  ];

  function stepIndex(id: string): number {
    return steps.findIndex((s) => s.id === id);
  }

  $: currentIndex = stepIndex(currentStep);
</script>

<div class="space-y-3">
  {#each steps as step, i}
    <div class="flex items-center gap-3">
      <div
        class="h-6 w-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0
               {i < currentIndex ? 'bg-green-500 text-white' :
                i === currentIndex ? 'bg-blue-500 text-white animate-pulse' :
                'bg-zinc-200 text-zinc-400'}"
      >
        {#if i < currentIndex}✓{:else}{i + 1}{/if}
      </div>
      <span
        class="text-sm {i === currentIndex ? 'font-semibold text-zinc-800' : 'text-zinc-400'}"
      >
        {step.label}
      </span>
    </div>
  {/each}
</div>
```

**Step 2: Commit**

```bash
git add frontend/src/lib/AnalysisProgress.svelte
git commit -m "feat: SSE progress indicator component"
```

---

## Task 10: Result Components (Vitals, Classification, Metrics)

**Files:**

- Create: `frontend/src/lib/VitalsCard.svelte`
- Create: `frontend/src/lib/ClassificationBadge.svelte`
- Create: `frontend/src/lib/MetricsTable.svelte`
- Create: `frontend/src/lib/types.ts`

**Step 1: Create types.ts**

```typescript
// frontend/src/lib/types.ts
export type DealCategory = "buyout" | "growth" | "minority";

export interface CompanyVitals {
  name: string | null;
  industry: string | null;
  sector: string | null;
  geography: string | null;
  founding_year: number | null;
  description: string | null;
}

export interface DealClassification {
  category: DealCategory;
  confidence: number;
  reasoning: string;
}

export interface BuyoutMetrics {
  revenue: string | null;
  ebitda: string | null;
  ebitda_margin: string | null;
  revenue_growth_rate: string | null;
  net_debt: string | null;
  leverage_ratio: string | null;
}

export interface GrowthMetrics {
  revenue: string | null;
  arr: string | null;
  mrr: string | null;
  revenue_growth_rate: string | null;
  gross_margin: string | null;
  net_revenue_retention: string | null;
  debt_levels: string | null;
}

export interface MinorityMetrics {
  revenue: string | null;
  ebitda: string | null;
  arr: string | null;
  revenue_growth_rate: string | null;
  ebitda_margin: string | null;
  gross_margin: string | null;
  debt_levels: string | null;
}

export interface DealAnalysis {
  vitals: CompanyVitals;
  classification: DealClassification;
  metrics: BuyoutMetrics | GrowthMetrics | MinorityMetrics;
}
```

**Step 2: Implement VitalsCard.svelte**

```svelte
<!-- frontend/src/lib/VitalsCard.svelte -->
<script lang="ts">
  import type { CompanyVitals } from './types';
  export let vitals: CompanyVitals;

  const fields: { label: string; key: keyof CompanyVitals }[] = [
    { label: 'Industry', key: 'industry' },
    { label: 'Sector', key: 'sector' },
    { label: 'Geography', key: 'geography' },
    { label: 'Founded', key: 'founding_year' },
  ];
</script>

<div class="rounded-xl border bg-white p-6 shadow-sm">
  <h2 class="text-xl font-bold text-zinc-900 mb-1">{vitals.name ?? '—'}</h2>
  {#if vitals.description}
    <p class="text-sm text-zinc-500 mb-4">{vitals.description}</p>
  {/if}
  <dl class="grid grid-cols-2 gap-x-4 gap-y-2">
    {#each fields as f}
      <dt class="text-xs font-medium text-zinc-400 uppercase tracking-wide">{f.label}</dt>
      <dd class="text-sm text-zinc-700">{vitals[f.key] ?? '—'}</dd>
    {/each}
  </dl>
</div>
```

**Step 3: Implement ClassificationBadge.svelte**

```svelte
<!-- frontend/src/lib/ClassificationBadge.svelte -->
<script lang="ts">
  import type { DealClassification } from './types';
  export let classification: DealClassification;

  const colours: Record<string, string> = {
    buyout:   'bg-purple-100 text-purple-800',
    growth:   'bg-green-100 text-green-800',
    minority: 'bg-blue-100 text-blue-800',
  };

  $: pct = Math.round(classification.confidence * 100);
</script>

<div class="rounded-xl border bg-white p-6 shadow-sm space-y-4">
  <div class="flex items-center justify-between">
    <span class="text-sm font-medium text-zinc-400 uppercase tracking-wide">Deal Type</span>
    <span class="rounded-full px-3 py-1 text-sm font-semibold {colours[classification.category] ?? 'bg-zinc-100 text-zinc-700'}">
      {classification.category.toUpperCase()}
    </span>
  </div>

  <div class="space-y-1">
    <div class="flex justify-between text-xs text-zinc-500">
      <span>Confidence</span>
      <span>{pct}%</span>
    </div>
    <div class="h-2 rounded-full bg-zinc-100 overflow-hidden">
      <div class="h-full rounded-full bg-blue-500 transition-all" style="width: {pct}%"></div>
    </div>
  </div>

  <p class="text-sm text-zinc-600 italic">{classification.reasoning}</p>
</div>
```

**Step 4: Implement MetricsTable.svelte**

```svelte
<!-- frontend/src/lib/MetricsTable.svelte -->
<script lang="ts">
  import type { BuyoutMetrics, GrowthMetrics, MinorityMetrics, DealCategory } from './types';
  export let metrics: BuyoutMetrics | GrowthMetrics | MinorityMetrics;
  export let category: DealCategory;

  const LABELS: Record<string, Record<string, string>> = {
    buyout: {
      revenue: 'Revenue',
      ebitda: 'EBITDA',
      ebitda_margin: 'EBITDA Margin',
      revenue_growth_rate: 'Revenue Growth',
      net_debt: 'Net Debt',
      leverage_ratio: 'Leverage Ratio (x)',
    },
    growth: {
      revenue: 'Revenue',
      arr: 'ARR',
      mrr: 'MRR',
      revenue_growth_rate: 'Revenue Growth',
      gross_margin: 'Gross Margin',
      net_revenue_retention: 'Net Revenue Retention',
      debt_levels: 'Debt Levels',
    },
    minority: {
      revenue: 'Revenue',
      ebitda: 'EBITDA',
      arr: 'ARR',
      revenue_growth_rate: 'Revenue Growth',
      ebitda_margin: 'EBITDA Margin',
      gross_margin: 'Gross Margin',
      debt_levels: 'Debt Levels',
    },
  };

  $: rows = Object.entries(LABELS[category] ?? {}).map(([key, label]) => ({
    label,
    value: (metrics as Record<string, string | null>)[key] ?? null,
  }));
</script>

<div class="rounded-xl border bg-white shadow-sm overflow-hidden">
  <div class="px-6 py-4 border-b flex items-center justify-between">
    <h3 class="font-semibold text-zinc-800">Key Metrics</h3>
  </div>
  <table class="w-full text-sm">
    <tbody>
      {#each rows as row, i}
        <tr class="{i % 2 === 0 ? 'bg-white' : 'bg-zinc-50'}">
          <td class="px-6 py-3 font-medium text-zinc-500 w-1/2">{row.label}</td>
          <td class="px-6 py-3 text-zinc-800 font-mono">{row.value ?? '—'}</td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>
```

**Step 5: Commit**

```bash
git add frontend/src/lib/
git commit -m "feat: result display components (vitals, classification, metrics)"
```

---

## Task 11: Main Page — Wire Everything Together

**Files:**

- Modify: `frontend/src/routes/+page.svelte`

**Step 1: Implement +page.svelte**

```svelte
<!-- frontend/src/routes/+page.svelte -->
<script lang="ts">
  import Dropzone from '$lib/Dropzone.svelte';
  import AnalysisProgress from '$lib/AnalysisProgress.svelte';
  import VitalsCard from '$lib/VitalsCard.svelte';
  import ClassificationBadge from '$lib/ClassificationBadge.svelte';
  import MetricsTable from '$lib/MetricsTable.svelte';
  import type { DealAnalysis } from '$lib/types';

  type AppState = 'idle' | 'analyzing' | 'results' | 'error';

  let state: AppState = 'idle';
  let currentStep = '';
  let selectedFiles: File[] = [];
  let result: DealAnalysis | null = null;
  let errorMessage = '';

  function onFiles(e: CustomEvent<File[]>) {
    selectedFiles = e.detail;
  }

  async function analyze() {
    if (!selectedFiles.length) return;
    state = 'analyzing';
    currentStep = 'extracting';
    result = null;
    errorMessage = '';

    const formData = new FormData();
    for (const file of selectedFiles) {
      formData.append('files', file);
    }

    try {
      const response = await fetch('/analyze', { method: 'POST', body: formData });

      if (!response.ok || !response.body) {
        throw new Error(`Server error: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const event = JSON.parse(line.slice(6));

          if (event.type === 'progress') {
            currentStep = event.step;
          } else if (event.type === 'result') {
            result = event.data as DealAnalysis;
            state = 'results';
          } else if (event.type === 'error') {
            throw new Error(event.message);
          }
        }
      }
    } catch (err) {
      errorMessage = err instanceof Error ? err.message : String(err);
      state = 'error';
    }
  }

  function reset() {
    state = 'idle';
    selectedFiles = [];
    result = null;
    errorMessage = '';
    currentStep = '';
  }

  function copyJson() {
    if (result) navigator.clipboard.writeText(JSON.stringify(result, null, 2));
  }
</script>

<svelte:head>
  <title>PE Deal Analyzer</title>
</svelte:head>

<div class="min-h-screen bg-zinc-50">
  <header class="border-b bg-white px-6 py-4">
    <div class="max-w-3xl mx-auto flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-zinc-900">PE Deal Analyzer</h1>
        <p class="text-xs text-zinc-400">Private Equity Deal Sourcing Assistant</p>
      </div>
    </div>
  </header>

  <main class="max-w-3xl mx-auto px-6 py-10 space-y-6">

    {#if state === 'idle'}
      <Dropzone on:files={onFiles} />

      {#if selectedFiles.length > 0}
        <div class="rounded-lg bg-white border p-4 text-sm text-zinc-600">
          <p class="font-medium text-zinc-800 mb-2">{selectedFiles.length} file(s) selected:</p>
          <ul class="list-disc list-inside space-y-1">
            {#each selectedFiles as f}
              <li>{f.name}</li>
            {/each}
          </ul>
        </div>
      {/if}

      <button
        on:click={analyze}
        disabled={!selectedFiles.length}
        class="w-full rounded-lg bg-zinc-900 py-3 text-sm font-semibold text-white
               hover:bg-zinc-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        Analyze Deal
      </button>
    {/if}

    {#if state === 'analyzing'}
      <div class="rounded-xl border bg-white p-8 shadow-sm">
        <h2 class="font-semibold text-zinc-800 mb-6">Analyzing deal documents...</h2>
        <AnalysisProgress {currentStep} />
      </div>
    {/if}

    {#if state === 'results' && result}
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <VitalsCard vitals={result.vitals} />
        <ClassificationBadge classification={result.classification} />
      </div>
      <MetricsTable metrics={result.metrics} category={result.classification.category} />

      <div class="flex gap-3">
        <button
          on:click={copyJson}
          class="rounded-lg border px-4 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-100 transition-colors"
        >
          Copy JSON
        </button>
        <button
          on:click={reset}
          class="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white hover:bg-zinc-700 transition-colors"
        >
          Analyze Another Deal
        </button>
      </div>
    {/if}

    {#if state === 'error'}
      <div class="rounded-xl border border-red-200 bg-red-50 p-6">
        <p class="font-semibold text-red-700 mb-1">Analysis failed</p>
        <p class="text-sm text-red-600">{errorMessage}</p>
      </div>
      <button
        on:click={reset}
        class="rounded-lg border px-4 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-100"
      >
        Try Again
      </button>
    {/if}

  </main>
</div>
```

**Step 2: Run frontend type check**

```bash
cd frontend && npx svelte-check --tsconfig ./tsconfig.json
```

Expected: No errors.

**Step 3: Commit**

```bash
cd /Users/mikeh/Downloads/pe_deal_analysis
git add frontend/src/routes/+page.svelte
git commit -m "feat: main page with idle/analyzing/results state machine"
```

---

## Task 12: End-to-End Smoke Test

**Step 1: Start the backend**

```bash
cd /Users/mikeh/Downloads/pe_deal_analysis
uv run uvicorn backend.main:app --reload --port 8000
```

**Step 2: Start the frontend (separate terminal)**

```bash
cd frontend && npm run dev
```

**Step 3: Open http://localhost:5173**

- Drop a PDF or DOCX onto the dropzone
- Click "Analyze Deal"
- Verify: progress steps animate, results appear with company vitals + classification + metrics
- Click "Copy JSON" — verify clipboard contains valid JSON
- Click "Analyze Another Deal" — verify app resets to idle state

**Step 4: Test /health endpoint**

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","provider":"...","model":"..."}`

**Step 5: Run full test suite one last time**

```bash
cd /Users/mikeh/Downloads/pe_deal_analysis
uv run pytest tests/ -v
```

Expected: All tests PASS.

**Step 6: Final commit**

```bash
git add .
git commit -m "feat: PE Deal Analyzer — complete implementation"
```

---

## Summary

| #   | Task              | Key Output                        |
| --- | ----------------- | --------------------------------- |
| 1   | Scaffolding       | pyproject.toml, .env, dirs        |
| 2   | config.py         | pydantic-settings env loading     |
| 3   | models.py         | All Pydantic schemas              |
| 4   | extraction.py     | markitdown + pymupdf4llm fallback |
| 5   | agents.py         | 3 pydantic-ai agents + pipeline   |
| 6   | main.py           | FastAPI SSE endpoint              |
| 7   | Frontend scaffold | SvelteKit + Tailwind + shadcn     |
| 8   | Dropzone          | File upload component             |
| 9   | AnalysisProgress  | SSE progress component            |
| 10  | Result components | Vitals, Classification, Metrics   |
| 11  | Main page         | Full state machine                |
| 12  | E2E smoke test    | Running app verified              |
