from datetime import UTC, datetime

from pydantic import HttpUrl, TypeAdapter

from app.providers.fundamentals.base import FinancialDataProvider
from app.schemas.financial import FinancialMetrics, MetricValue


class MockFinancialDataProvider(FinancialDataProvider):
    name = "mock_financials"
    source_url: HttpUrl = TypeAdapter(HttpUrl).validate_python(
        "https://example.test/mock-financials"
    )

    async def get_financials(self, ticker: str) -> FinancialMetrics:
        normalized = ticker.strip().upper()
        now = datetime.now(UTC)

        def metric(value: float, source: str = "mock_financials") -> MetricValue:
            return MetricValue(
                value=value,
                source=source,
                source_url=self.source_url,
                as_of=now,
                retrieved_at=now,
            )

        return FinancialMetrics(
            ticker=normalized,
            currency="USD",
            revenue=metric(120_000_000),
            revenue_growth=metric(0.2),
            eps=metric(2.5),
            eps_growth=metric(0.25),
            gross_margin=metric(0.4),
            operating_margin=metric(0.2),
            net_income=metric(15_000_000),
            free_cash_flow=metric(32_000_000),
            fcf_growth=metric(0.28),
            pe=metric(24.0),
            forward_pe=metric(20.0),
            peg=metric(1.2),
            limitations=["Mock financial data is for local development only."],
        )
