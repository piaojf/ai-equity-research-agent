# AI Equity Research Agent Architecture

## Development and production deployment

Local development runs natively on Windows. Backend tests and mock-mode API
smoke tests do not require Docker or external services. `DATA_MODE=mock` starts
without API keys and the default test suite does not call external APIs.

The final production target is a Linux VPS using Docker Compose, Nginx and
HTTPS. The Compose topology is deliberately retained as a future deployment
boundary rather than a local Phase 1 dependency:

```text
Internet -> HTTPS -> nginx
                    |-> frontend
                    |-> backend -> postgres
                    |             -> qdrant
                    |             -> redis -> worker
                    |                         -> LangGraph workflow
                    |                         -> postgres ResearchReport
```

Only Nginx publishes ports 80 and 443. Vercel and Render are optional README
alternatives, not the primary deployment target.

## Request and background-job architecture

Synchronous application requests follow Route -> Service -> Provider or
Repository. `POST /api/deep-research` is designed as an asynchronous boundary:

```text
FastAPI -> ResearchTask(queued) -> Redis Queue -> Worker
                                      Worker -> LangGraph Deep Research Workflow
                                      Worker -> PostgreSQL ResearchReport
```

ARQ is the selected low-complexity queue option for the Linux deployment entry
point. Dramatiq and Celery remain alternatives if operations require them. The
local API currently uses an in-memory queue for deterministic development;
durable production task/report updates are an explicit follow-up.

## Data-source boundaries

All external data access is behind a provider interface:

- `MarketDataProvider`: Yahoo or Finnhub market prices and history.
- `FinancialDataProvider`: SEC Company Facts fundamentals.
- `SECProvider`: SEC EDGAR filing metadata and filing text.
- `NewsProvider`: Finnhub or another news provider.
- `MacroProvider`: FRED in a later phase.

Yahoo Finance is not the universal source for financial fundamentals. SEC
Company Facts is preferred for normalized fundamentals, while EDGAR handles
filings and citations.

## Phase 2 market data

`GET /api/stocks/{ticker}` follows:

```text
Route -> MarketService -> MarketProviderRegistry -> MarketDataProvider
      -> PriceSnapshot + HistoricalPricePoint -> ApiResponse[StockOverview]
```

Phase 2 has deterministic mock data and an Alpha Vantage adapter. Provider
selection is configuration-driven and never silently falls back in `real`
mode. Provider errors are converted to domain errors before reaching a route.

## Phase 3 financial data and scoring

Financial fundamentals follow the same boundary:

```text
FinancialService -> FinancialProviderRegistry -> FinancialDataProvider
                                           |-> MockFinancialDataProvider
                                           |-> SECCompanyFactsProvider
```

The SEC adapter resolves CIKs, filters annual 10-K facts, normalizes revenue,
EPS, margins, net income and free cash flow, and preserves source metadata.
Valuation metrics unavailable from Company Facts remain null with a limitation.
Malformed or incompatible facts are excluded rather than converted to zeros.

The scoring engine is deterministic Python code. Each score includes a
`ScoreBreakdown` with raw value, normalized score, weight, contribution, source,
missing metrics and confidence. Missing metrics cause explicit weight
renormalization. An LLM may explain the result but never changes the numeric
score.

## SEC citation model

Citation identity is filing- and chunk-based rather than PDF-page-based:

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

## Phase scope and roadmap

The canonical contracts are in [shared-contracts.md](shared-contracts.md), and
implementation ownership is in [dependency-dag.md](dependency-dag.md).

1. Phase 1: FastAPI foundation, configuration, logging, request IDs, errors,
   health endpoint, schemas, tests and local native development.
2. Phase 2: Market price provider, registry, Stock Overview API and contracts.
3. Phase 3: SEC Company Facts normalization, financial service and explainable
   scoring.
4. Phase 4: LangGraph research agent and structured output.
5. Phase 5: PostgreSQL persistence and repositories.
6. Phase 6: SEC RAG and citations.
7. Phase 7: Redis queue and Deep Research Worker.
8. Phase 8: Frontend dashboard.
9. Phase 9: Linux VPS Docker Compose, Nginx, HTTPS and operations.
10. Phase 10: Integration QA and portfolio polish. **Complete.**
