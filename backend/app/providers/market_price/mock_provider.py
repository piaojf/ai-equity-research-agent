from datetime import UTC, date, datetime

from app.providers.exceptions import InvalidTickerError
from app.providers.market_price.base import MarketDataProvider
from app.schemas.market import HistoricalPricePoint, PriceSnapshot

_AS_OF = datetime(2026, 9, 14, 20, 0, tzinfo=UTC)

_MOCK_SERIES: dict[str, tuple[tuple[date, float, float, float, float, int], ...]] = {
    "NVDA": (
        (date(2026, 9, 8), 169.0, 173.0, 168.0, 172.0, 42_100_000),
        (date(2026, 9, 9), 172.0, 176.0, 171.0, 175.0, 39_800_000),
        (date(2026, 9, 10), 175.0, 178.0, 173.0, 174.0, 44_500_000),
        (date(2026, 9, 11), 174.0, 181.0, 173.0, 180.0, 48_200_000),
        (date(2026, 9, 14), 180.0, 184.0, 179.0, 182.0, 51_300_000),
    ),
    "AAPL": (
        (date(2026, 9, 8), 234.0, 237.0, 233.0, 236.0, 21_400_000),
        (date(2026, 9, 9), 236.0, 238.0, 235.0, 237.0, 20_100_000),
        (date(2026, 9, 10), 237.0, 239.0, 234.0, 235.0, 23_700_000),
        (date(2026, 9, 11), 235.0, 240.0, 234.0, 239.0, 25_200_000),
        (date(2026, 9, 14), 239.0, 242.0, 238.0, 241.0, 24_900_000),
    ),
    "MSFT": (
        (date(2026, 9, 8), 511.0, 516.0, 509.0, 514.0, 18_500_000),
        (date(2026, 9, 9), 514.0, 518.0, 512.0, 516.0, 17_900_000),
        (date(2026, 9, 10), 516.0, 519.0, 511.0, 513.0, 19_700_000),
        (date(2026, 9, 11), 513.0, 520.0, 512.0, 518.0, 21_100_000),
        (date(2026, 9, 14), 518.0, 523.0, 517.0, 521.0, 20_800_000),
    ),
    "TSLA": (
        (date(2026, 9, 8), 331.0, 338.0, 329.0, 336.0, 31_700_000),
        (date(2026, 9, 9), 336.0, 341.0, 333.0, 339.0, 29_400_000),
        (date(2026, 9, 10), 339.0, 342.0, 331.0, 333.0, 34_800_000),
        (date(2026, 9, 11), 333.0, 347.0, 332.0, 345.0, 41_200_000),
        (date(2026, 9, 14), 345.0, 350.0, 341.0, 348.0, 38_600_000),
    ),
    "AMD": (
        (date(2026, 9, 8), 172.0, 176.0, 170.0, 174.0, 27_900_000),
        (date(2026, 9, 9), 174.0, 179.0, 173.0, 178.0, 26_100_000),
        (date(2026, 9, 10), 178.0, 180.0, 174.0, 175.0, 28_400_000),
        (date(2026, 9, 11), 175.0, 183.0, 174.0, 181.0, 32_700_000),
        (date(2026, 9, 14), 181.0, 185.0, 179.0, 183.0, 30_500_000),
    ),
}


class MockMarketProvider(MarketDataProvider):
    name = "mock"
    source_url = None

    def _series(
        self,
        ticker: str,
    ) -> tuple[tuple[date, float, float, float, float, int], ...]:
        normalized = ticker.strip().upper()
        try:
            return _MOCK_SERIES[normalized]
        except KeyError as exc:
            raise InvalidTickerError(normalized) from exc

    async def get_quote(self, ticker: str) -> PriceSnapshot:
        series = self._series(ticker)
        latest = series[-1]
        previous = series[-2]
        change = latest[4] - previous[4]
        return PriceSnapshot(
            ticker=ticker.strip().upper(),
            price=latest[4],
            previous_close=previous[4],
            change=change,
            change_percent=change / previous[4] * 100,
            open=latest[1],
            high=latest[2],
            low=latest[3],
            volume=latest[5],
            currency="USD",
            as_of=datetime(latest[0].year, latest[0].month, latest[0].day, tzinfo=UTC),
            retrieved_at=_AS_OF,
            source=self.name,
            is_delayed=True,
        )

    async def get_history(
        self,
        ticker: str,
        period: str,
    ) -> list[HistoricalPricePoint]:
        del period
        return [
            HistoricalPricePoint(
                date=item[0],
                open=item[1],
                high=item[2],
                low=item[3],
                close=item[4],
                volume=item[5],
            )
            for item in self._series(ticker)
        ]
