# Local Demo Readiness / Reality Check

Date: 2026-09-16

This report records observed runtime behavior. It does not mark mocked,
in-memory, or static behavior as real-provider acceptance.

## A. Frontend

| Check | Result |
| --- | --- |
| Node | `v24.19.0` |
| npm | `11.17.0` |
| `npm install` | exit 0 |
| `npm run lint` | exit 0 |
| `npm run typecheck` | exit 0 |
| `npm run build` | exit 0 |
| Browser runtime | landing, stock, compare, SEC Ask, and Deep Research returned HTTP 200; interactive flows were exercised in the Codex browser panel |
| Search | client-side ticker search is wired to `/stock/{ticker}` |
| Stock detail | fetches market and research APIs at runtime |
| SEC Ask | input, loading, success, error, low-evidence and citation rendering are wired |
| Deep Research | task creation, polling, queued/running/completed/failed rendering are wired |

The Next build emitted a Windows SWC native-binary warning and used its
fallback path; build, lint, and typecheck still exited successfully.

## B. Market data

The default real provider is `YahooFinanceMarketProvider`, behind
`MarketDataProvider`. Live requests returned `source=yahoo_finance`,
`is_delayed=true`, valid prices, timestamps, and 63 three-month OHLCV points
for all required symbols:

```text
NVDA 210.96
AAPL 333.08
MSFT 505.41
TSLA 358.97
AMD  493.41
```

The live API smoke used `GET /api/stocks/{ticker}` and returned HTTP 200 for
all five tickers. Alpha Vantage remains available as an explicit keyed adapter.

## C. Financial data and scoring

SEC Company Facts returned real metrics for NVDA and AMD through
`SECCompanyFactsProvider`. Missing valuation metrics (`pe`, `forward_pe`, and
`peg`) remained unavailable with explicit limitations. No LLM filled missing
fields.

The live `POST /api/research` smoke returned HTTP 200, real market source,
real SEC Company Facts source, valid `ScoreBreakdown` objects, and an overall
score. Growth components remained traceable to revenue growth, EPS growth, and
FCF growth.

## D. AI research

LangGraph executed through the research nodes and Pydantic structured output
validated successfully. The real-mode result used the configured DeepSeek
report interpreter through the existing LLM boundary. The deterministic
scoring engine still owns all numeric scores; the LLM only interprets the
structured report.

## E. SEC RAG

The real SEC EDGAR pipeline was exercised for NVDA's latest 10-K:

```text
filing_date=2026-02-25
accession_number=0001045810-26-000021
source_url=https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm
html_chars=1967816
chunks=356
retrieved_citations=3
```

The real-mode path used `QdrantVectorStore` against the local HTTP service at
`http://127.0.0.1:6333`. The target 10-K produced 356 chunks and 356 points;
running ingestion a second time left the target accession at 356 points.
Collection status was `green`, vector dimension was 32, and distance was
Cosine. Retrieval returned three Qdrant citations with scores before DeepSeek
generated the evidence-only answer.

Deep Research used the same collection with query text `Why did NVDA fall
recently?`, ticker filter `NVDA`, filing filter `10-K`, top-k 5, and no score
threshold. Retrieved chunks were `279`, `51`, `263`, `105`, and `175`, with
scores from `0.896402` to `0.908038`. No candidate was discarded during
normalization.

## F. Deep Research and persistence

`POST /api/deep-research` returned HTTP 202 with `task_id` and `request_id`.
The real API submission moved through `queued`, `running`, and `completed`,
created a durable `ResearchReport`, and used the running ARQ worker. Price
analysis resolved the Yahoo history to `2026-06-16..2026-09-14` and detected
18 events using the unchanged 5% daily/5-day threshold. The latest detected
event was `2026-09-14` with a five-day change of `-0.084216`.

For task `5be97bc7-7a45-457e-9fa2-364ca5c76a0d`, the report contained five SEC
evidence items and five linked major events. DeepSeek synthesis was called
with `evidence_count=5` and returned a medium-confidence, evidence-only
conclusion.

Redis returned `PING=True`. Real mode used `RedisTaskQueue` and the running ARQ
worker; PostgreSQL remained the source of truth for durable task and report
status. A controlled invalid-ticker job reached `failed` with structured
`INVALID_TICKER` data instead of remaining `running`.

PostgreSQL 17 is running locally with the `equity` role and
`ai_equity_research` database. Alembic revision `338255031ae5` is applied, and
the live tables include `companies`, `filings`, `research_tasks`, and
`research_reports`.

## G. Acceptance state

```text
LOCAL DEMO READY: FULL
```

Passed: frontend interactive flows/build, real market data, real financial data,
deterministic scoring, LangGraph execution, SEC EDGAR/chunking/Qdrant RAG,
HTTP 202 lifecycle, PostgreSQL repository persistence, Redis/ARQ-backed worker,
DeepSeek SEC Ask, DeepSeek Deep Research synthesis with five SEC evidence
items, browser Stock/AI Research/SEC Ask/Compare/Deep Research/Error flows,
pytest, Ruff, and mypy.

No Phase 11 was created and no product scope was added. Docker was not run in
the local-development phase.
