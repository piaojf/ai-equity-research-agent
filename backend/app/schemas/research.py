from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.schemas.financial import FinancialMetrics
from app.schemas.market import StockOverview
from app.schemas.scoring import ScoreBreakdown


class ResearchRequest(BaseModel):
    """Validated input to the research graph."""

    model_config = ConfigDict(extra="forbid", strict=True)

    ticker: str = Field(min_length=1, max_length=10)
    question: str | None = Field(default=None, max_length=2_000)
    include_sec_research: bool = False


class ResearchIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    ticker: str = Field(min_length=1, max_length=10)
    question: str | None = Field(default=None, max_length=2_000)
    include_sec_research: bool


class NewsItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    headline: str = Field(min_length=1, max_length=500)
    source: str = Field(min_length=1, max_length=200)
    published_at: datetime | None = None
    source_url: HttpUrl | None = None


class NewsAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    status: Literal["available", "not_configured", "unavailable"]
    articles: list[NewsItem] = Field(default_factory=list, max_length=50)
    summary: str = Field(default="", max_length=4_000)
    limitations: list[str] = Field(default_factory=list, max_length=50)


class Citation(BaseModel):
    """Filing identity for future SEC RAG evidence."""

    model_config = ConfigDict(extra="forbid", strict=True)

    ticker: str = Field(min_length=1, max_length=10)
    filing_type: Literal["10-K", "10-Q"]
    filing_date: date
    accession_number: str = Field(min_length=1, max_length=64)
    section: str = Field(min_length=1, max_length=200)
    chunk_id: str = Field(min_length=1, max_length=200)
    source_url: HttpUrl
    excerpt: str = Field(min_length=1, max_length=10_000)
    page_or_anchor: str | None = Field(default=None, max_length=200)


class SecResearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    status: Literal["available", "not_configured", "unavailable"]
    summary: str = Field(default="", max_length=4_000)
    citations: list[Citation] = Field(default_factory=list, max_length=50)
    limitations: list[str] = Field(default_factory=list, max_length=50)


class ReportInterpretation(BaseModel):
    """Narrative-only LLM output; deterministic scores are never accepted here."""

    model_config = ConfigDict(extra="forbid", strict=True)

    summary: str = Field(min_length=1, max_length=4_000)
    fundamental_view: str = Field(default="", max_length=4_000)
    valuation_view: str = Field(default="", max_length=4_000)
    sentiment: str = Field(default="", max_length=4_000)
    thesis: list[str] = Field(min_length=1, max_length=10)
    risks: list[str] = Field(min_length=1, max_length=10)
    catalysts: list[str] = Field(min_length=1, max_length=10)


class ResearchContext(BaseModel):
    """Read-only context exposed to the narrative interpreter."""

    model_config = ConfigDict(extra="forbid", strict=True)

    ticker: str = Field(min_length=1, max_length=10)
    market_data: StockOverview | None = None
    financial_metrics: FinancialMetrics | None = None
    scores: dict[str, ScoreBreakdown]
    news: NewsAnalysis
    sec_research: SecResearchResult | None = None
    limitations: list[str] = Field(default_factory=list, max_length=100)


class EquityResearchReport(BaseModel):
    """Strict, auditable report assembled from tool results and fixed scores."""

    model_config = ConfigDict(extra="forbid", strict=True)

    ticker: str = Field(min_length=1, max_length=10)
    generated_at: datetime
    summary: str = Field(min_length=1, max_length=4_000)
    fundamental_score: ScoreBreakdown
    growth_score: ScoreBreakdown
    valuation_score: ScoreBreakdown
    risk_score: ScoreBreakdown
    sentiment_score: ScoreBreakdown | None = None
    fundamental_view: str = Field(default="", max_length=4_000)
    valuation_view: str = Field(default="", max_length=4_000)
    sentiment: str = Field(default="", max_length=4_000)
    thesis: list[str] = Field(min_length=1, max_length=10)
    risks: list[str] = Field(min_length=1, max_length=10)
    catalysts: list[str] = Field(min_length=1, max_length=10)
    scores: dict[str, ScoreBreakdown]
    overall_score: ScoreBreakdown
    market_data: StockOverview | None = None
    financial_metrics: FinancialMetrics | None = None
    news: NewsAnalysis
    sec_research: SecResearchResult | None = None
    key_metrics: dict[str, float | None] = Field(default_factory=dict)
    data_sources: list[str] = Field(default_factory=list, max_length=100)
    confidence: Literal["low", "medium", "high"]
    errors: list[str] = Field(default_factory=list, max_length=100)
    limitations: list[str] = Field(default_factory=list, max_length=100)
