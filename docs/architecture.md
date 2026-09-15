# AI Equity Research Agent Architecture

## Current development mode

Local development runs natively on the developer workstation. Phase 1 does not
use Docker, Docker Compose, Nginx, Redis, PostgreSQL, Qdrant, Frontend, or a
Worker process.

```text
Windows workstation
└── FastAPI backend
```

The backend starts with `DATA_MODE=mock` and does not require external API
keys. Tests never call external services. Phase 2 adds a standalone backend
Dockerfile only because the phase acceptance requires a backend image check;
full Compose and Linux deployment remain deferred.

## Final Linux deployment target

When the project is ready for online deployment, the primary target is a Linux
VPS running Docker Compose:

```text
Internet
   ↓ HTTPS
 Nginx
   ├── /      → Frontend
   └── /api/  → Backend

Backend → PostgreSQL
Backend → Qdrant
Backend → Redis Queue
Redis Queue → Worker → LangGraph Deep Research Workflow
Worker → PostgreSQL ResearchReport
```

Only Nginx publishes ports 80 and 443. Application and data services stay on
the private Compose network. Vercel and Render may be documented as optional
alternatives, but they are not the primary deployment path.

## Deep Research background jobs

`POST /api/deep-research` creates a `ResearchTask` with `queued` status and
returns HTTP 202 with `task_id` and `request_id`. A future Worker consumes a
small Redis message containing those identifiers, executes the LangGraph
workflow, and persists `ResearchReport` in PostgreSQL.

```text
FastAPI → ResearchTask(queued) → Redis Queue → Worker
       → LangGraph Deep Research → ResearchReport(PostgreSQL)
```

The queue is represented by a `TaskQueue` interface. ARQ is the preferred
low-complexity candidate for the later implementation; Dramatiq and Celery
remain alternatives if operational requirements expand. No queue library or
Worker is part of Phase 1.

## Data-source boundaries

External APIs are accessed only through Provider interfaces:

- `MarketPriceProvider`: Yahoo or Finnhub price and history data.
- `FinancialFundamentalProvider`: SEC Company Facts as the preferred source.
- `SECProvider`: SEC EDGAR filing metadata and filing text.
- `NewsProvider`: Finnhub or another news provider.
- `MacroProvider`: FRED in a later phase.

Yahoo is not the universal source for fundamentals. Financial facts and filing
content remain separate provider responsibilities.

## Phase 2 market data architecture

The Stock Overview request follows this path:

```text
GET /api/stocks/{ticker}
        ↓
MarketService
        ↓
MarketProviderRegistry
        ↓
MarketDataProvider
        ↓
PriceSnapshot + HistoricalPricePoint
        ↓
ApiResponse[StockOverview]
```

The provider protocol is intentionally small:

```python
class MarketDataProvider(Protocol):
    name: str
    source_url: HttpUrl | None

    async def get_quote(self, ticker: str) -> PriceSnapshot: ...
    async def get_history(
        self, ticker: str, period: str
    ) -> list[HistoricalPricePoint]: ...
```

Phase 2 includes a deterministic `MockMarketProvider` for NVDA, AAPL, MSFT,
TSLA, and AMD. It uses fixed OHLCV values and always labels responses with
`source="mock"`.

The only real provider is `AlphaVantageMarketProvider`. It maps
`GLOBAL_QUOTE` and `TIME_SERIES_DAILY` into internal Pydantic schemas, marks
daily quote data as delayed/latest-available, and never includes the API key
in `source_url`. Alpha Vantage documents `GLOBAL_QUOTE` and daily OHLCV
endpoints as requiring an API key; realtime and historical freshness are
represented explicitly rather than inferred.[Alpha Vantage API Documentation](https://www.alphavantage.co/documentation/)

Provider selection is configuration-driven:

```text
DATA_MODE=mock   → MockMarketProvider
DATA_MODE=real   → AlphaVantageMarketProvider
DATA_MODE=hybrid → AlphaVantageMarketProvider when configured,
                   otherwise explicitly labelled MockMarketProvider
```

The service retries timeout, rate-limit, and provider-unavailable errors using
the configured two-retry exponential-backoff policy. Provider exceptions are
mapped to domain errors before reaching the API response.

## Explainable scoring

Core numeric scores are calculated by Python. LLM output is limited to
interpretation and narrative explanation.

```python
class ScoreComponent(BaseModel):
    metric: str
    raw_value: float | None
    normalized_score: float | None
    weight: float
    contribution: float
    source: str
    source_url: HttpUrl | None = None

class ScoreBreakdown(BaseModel):
    score_name: str
    final_score: int
    components: list[ScoreComponent]
    methodology_version: str
    missing_metrics: list[str]
```

Each contribution is `normalized_score * weight`. Missing metrics are recorded
and weights are re-normalized; the LLM never invents missing numbers.

## SEC citation model

SEC RAG citations use filing identity and chunk identity instead of relying on
traditional PDF page numbers:

```python
class Citation(BaseModel):
    ticker: str
    filing_type: Literal["10-K", "10-Q"]
    filing_date: date
    accession_number: str
    section: str
    chunk_id: str
    source_url: HttpUrl
    excerpt: str
    page_or_anchor: str | None = None
```

## Phase roadmap

1. Phase 1: FastAPI foundation, configuration, logging, request IDs, errors,
   health endpoint, base schemas, pytest, Ruff, mypy.
2. Phase 2: Market price Provider, Provider Registry, Stock Overview API, and
   contract tests.
3. Phase 3: SEC Company Facts normalization and explainable scoring.
4. Phase 4: LangGraph Research Agent and structured output.
5. Phase 5: PostgreSQL persistence and repositories.
6. Phase 6: SEC RAG and citations.
7. Phase 7: Redis queue and Deep Research Worker.
8. Phase 8: Frontend Dashboard.
9. Phase 9: Linux VPS Docker Compose, Nginx and HTTPS.
