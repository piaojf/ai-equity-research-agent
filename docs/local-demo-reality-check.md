# Local Demo Readiness / Reality Check

Date: 2026-09-15

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
| Browser runtime | landing, stock, compare, SEC Ask, and Deep Research returned HTTP 200; pages were opened in the Codex browser panel |
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
validated successfully. The local result used `MockReportInterpreter` because
no `OPENAI_API_KEY` or local LLM service was configured. Therefore the
real-LLM acceptance item is `SKIPPED: credential/service not configured`; the
existing `LLMReportInterpreter` interface remains the integration boundary.

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

Chunking, deterministic embeddings, in-memory retrieval, citation generation,
and low-evidence behavior executed; the real-mode SEC Ask route now lazily
ingests the latest filing before retrieval. Qdrant was not listening on
`127.0.0.1:6333`, so real Qdrant ingestion/retrieval is recorded as
`SKIPPED: Qdrant service not configured`, not as a passed production check.

## F. Deep Research and persistence

`POST /api/deep-research` returned HTTP 202 with `task_id` and `request_id`.
The local in-memory queue scheduled a worker task and the task reached
`completed` with an evidence-aware low-confidence report. Live market data was
used by the workflow.

Redis was installed locally and `redis-cli ping` returned `PONG`. The API's
local route still uses `InMemoryTaskQueue`; Redis/ARQ execution and durable
task status are not marked passed.

A temporary native PostgreSQL 17 cluster was used to verify repository
behavior: a completed `ResearchTask` and `ResearchReport` were written,
reopened through a new database connection, and the report score was restored.
The temporary cluster was stopped and removed after the check.

## G. Acceptance state

```text
LOCAL DEMO READY: PARTIAL
```

Passed: frontend runtime/build, real market data, real financial data,
deterministic scoring, LangGraph execution, SEC EDGAR/chunking/in-memory RAG,
HTTP 202 lifecycle, native PostgreSQL repository persistence, pytest, Ruff, and
mypy.

Not passed or skipped: real LLM, Qdrant-backed RAG, Redis/ARQ-backed API worker,
and browser click-level automation beyond the rendered runtime pages.

No Phase 11 was created. The remaining items are external runtime
configuration, not additional product scope.
