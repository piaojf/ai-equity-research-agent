from datetime import datetime

from pydantic import BaseModel, Field, FiniteFloat, HttpUrl


class MetricValue(BaseModel):
    value: FiniteFloat | None
    source: str = Field(min_length=1)
    source_url: HttpUrl | None = None
    as_of: datetime | None = None
    retrieved_at: datetime


class FinancialMetrics(BaseModel):
    ticker: str = Field(min_length=1)
    currency: str | None = None
    revenue: MetricValue | None = None
    revenue_growth: MetricValue | None = None
    eps: MetricValue | None = None
    eps_growth: MetricValue | None = None
    gross_margin: MetricValue | None = None
    operating_margin: MetricValue | None = None
    net_income: MetricValue | None = None
    free_cash_flow: MetricValue | None = None
    fcf_growth: MetricValue | None = None
    pe: MetricValue | None = None
    forward_pe: MetricValue | None = None
    peg: MetricValue | None = None
    limitations: list[str] = Field(default_factory=list)
