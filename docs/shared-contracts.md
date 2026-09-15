# Shared Contracts

This document is the canonical contract for Phases 3-10. New modules reuse
these names and meanings instead of introducing duplicate schemas.

## Dependency direction

```text
API Route -> Application Service -> Tool or Repository -> Provider or Storage
```

Routes do not call providers, repositories, LLMs, Redis, Qdrant or external
HTTP APIs directly.

## Common invariants

- Every API response uses `ApiResponse[T]` or `ErrorResponse`.
- Every request carries `request_id`; it is present in response JSON and logs.
- External-data objects preserve source, source URL when available, as-of time
  and retrieval time.
- `DATA_MODE=mock` is deterministic and never calls a network provider.
- `DATA_MODE=real` never silently falls back to Mock.
- `DATA_MODE=hybrid` may fall back only when the response explicitly identifies
  the mock source.
- Provider exceptions become `AppError` before reaching an API client.
- Financial numbers come from provider data or Python rules, never LLM guesses.

## Provider interfaces

```python
class FinancialDataProvider(Protocol):
    name: str
    async def get_financials(self, ticker: str) -> FinancialMetrics: ...

class NewsProvider(Protocol):
    name: str
    async def get_latest(self, ticker: str, limit: int) -> list[NewsArticle]: ...
    async def search_between(self, ticker: str, start: date, end: date) -> list[NewsArticle]: ...

class SECProvider(Protocol):
    name: str
    async def list_filings(self, ticker: str, forms: list[str]) -> list[FilingMetadata]: ...
    async def fetch_filing(self, filing: FilingMetadata) -> str: ...

class LLMProvider(Protocol):
    name: str
    async def generate_structured(self, *, system_prompt: str, user_prompt: str, schema: type[BaseModel]) -> BaseModel: ...
```

The existing `MarketDataProvider` contract remains in the backend market
provider module and is unchanged.

## FinancialMetrics

Every metric is nullable. Missing data is `None`, never zero.

```python
class MetricValue(BaseModel):
    value: float | None
    source: str
    source_url: HttpUrl | None = None
    as_of: datetime | None = None
    retrieved_at: datetime

class FinancialMetrics(BaseModel):
    ticker: str
    currency: str | None
    revenue: MetricValue | None
    revenue_growth: MetricValue | None
    eps: MetricValue | None
    eps_growth: MetricValue | None
    gross_margin: MetricValue | None
    operating_margin: MetricValue | None
    net_income: MetricValue | None
    free_cash_flow: MetricValue | None
    fcf_growth: MetricValue | None
    pe: MetricValue | None
    forward_pe: MetricValue | None
    peg: MetricValue | None
    limitations: list[str]
```

## Explainable scoring

`ScoreBreakdown` stores score name, final score, components, methodology
version, missing metrics, limitations and confidence. Each component stores
`raw_value`, `normalized_score`, `weight`, `contribution`, `source` and an
optional source URL. Contributions equal normalized score times weight, and
available component weights sum to one after missing-metric renormalization.

LLMs may explain a `ScoreBreakdown` but may not alter its numeric fields.

## Research and evidence schemas

Reserved canonical names:

- `NewsArticle`: ticker, title, source, published_at, URL, summary.
- `FilingMetadata`: ticker, filing type, filing date, accession number, URL.
- `Citation`: ticker, filing type, filing date, accession number, section,
  chunk ID, source URL, excerpt and optional page or anchor.
- `EquityResearchReport`: ticker, deterministic scores, views, summary,
  catalysts, risks, key metrics, data sources, confidence and errors.
- `DeepResearchReport`: ticker, question, conclusion, major events, evidence,
  confidence and limitations.

## Error and configuration contract

Existing error codes remain stable. Future phases may add codes but must not
rename existing values:

```text
INVALID_TICKER PROVIDER_TIMEOUT PROVIDER_RATE_LIMIT MARKET_DATA_UNAVAILABLE
CONFIGURATION_ERROR FINANCIAL_DATA_UNAVAILABLE NEWS_PROVIDER_UNAVAILABLE
SEC_DATA_UNAVAILABLE LLM_ERROR DATABASE_ERROR QUEUE_UNAVAILABLE QDRANT_ERROR
VALIDATION_ERROR HTTP_ERROR INTERNAL_ERROR
```

Configuration uses `pydantic-settings`. Secrets use `SecretStr`, load from
environment variables and are never logged.
