from typing import Protocol

from app.schemas.financial import FinancialMetrics


class FinancialDataProvider(Protocol):
    name: str

    async def get_financials(self, ticker: str) -> FinancialMetrics: ...
