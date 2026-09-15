from typing import Protocol

from pydantic import HttpUrl

from app.schemas.market import HistoricalPricePoint, PriceSnapshot


class MarketDataProvider(Protocol):
    name: str
    source_url: HttpUrl | None

    async def get_quote(self, ticker: str) -> PriceSnapshot: ...

    async def get_history(
        self,
        ticker: str,
        period: str,
    ) -> list[HistoricalPricePoint]: ...
