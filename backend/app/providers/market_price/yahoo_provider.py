from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import HttpUrl, TypeAdapter, ValidationError

from app.providers.exceptions import (
    InvalidTickerError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.market_price.base import MarketDataProvider
from app.schemas.market import HistoricalPricePoint, PriceSnapshot


class YahooFinanceMarketProvider(MarketDataProvider):
    """Market-price adapter for Yahoo's chart endpoint."""

    name = "yahoo_finance"
    base_url = "https://query1.finance.yahoo.com/v8/finance/chart"
    source_url: HttpUrl | None = None

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
        proxy_url: str | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self._client = client
        self.proxy_url = proxy_url

    def _source_url(self, ticker: str, period: str) -> HttpUrl:
        ranges = {"1m": "1mo", "3m": "3mo", "6m": "6mo", "1y": "1y"}
        query = f"?range={ranges.get(period, '3mo')}&interval=1d&events=history"
        return TypeAdapter(HttpUrl).validate_python(
            f"{self.base_url}/{ticker}{query}"
        )

    async def _request(self, ticker: str, period: str) -> dict[str, Any]:
        url = f"{self.base_url}/{ticker}"
        params = {
            "range": {"1m": "1mo", "3m": "3mo", "6m": "6mo", "1y": "1y"}.get(
                period, "3mo"
            ),
            "interval": "1d",
            "events": "history",
        }
        try:
            if self._client is not None:
                response = await self._client.get(url, params=params)
            else:
                async with httpx.AsyncClient(
                    timeout=self.timeout_seconds,
                    headers={"User-Agent": "AI-Equity-Research-Agent/0.1"},
                    proxy=self.proxy_url,
                ) as client:
                    response = await client.get(url, params=params)
            if response.status_code == 429:
                raise ProviderRateLimitError(self.name)
            if response.status_code >= 500:
                raise ProviderUnavailableError(self.name)
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(self.name) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(self.name) from exc
        except ValueError as exc:
            raise ProviderUnavailableError(
                self.name, "Provider returned invalid JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise ProviderUnavailableError(
                self.name, "Provider returned an invalid payload."
            )
        return payload

    async def _chart(self, ticker: str, period: str) -> tuple[dict[str, Any], HttpUrl]:
        normalized = ticker.strip().upper()
        payload = await self._request(normalized, period)
        chart = payload.get("chart")
        result = chart.get("result") if isinstance(chart, dict) else None
        error = chart.get("error") if isinstance(chart, dict) else None
        if (
            error
            or not isinstance(result, list)
            or not result
            or not isinstance(result[0], dict)
        ):
            raise InvalidTickerError(normalized)
        return result[0], self._source_url(normalized, period)

    @staticmethod
    def _number(value: Any, field_name: str) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ProviderUnavailableError(
                "yahoo_finance", f"Provider field '{field_name}' was not numeric."
            ) from exc
        if number <= 0:
            raise ProviderUnavailableError(
                "yahoo_finance", f"Provider field '{field_name}' was invalid."
            )
        return number

    @staticmethod
    def _volume(value: Any) -> int:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ProviderUnavailableError(
                "yahoo_finance", "Provider field 'volume' was not numeric."
            ) from exc
        if number < 0:
            raise ProviderUnavailableError(
                "yahoo_finance", "Provider field 'volume' was invalid."
            )
        return int(number)

    @staticmethod
    def _timestamp(value: Any, field_name: str) -> datetime:
        try:
            return datetime.fromtimestamp(int(value), tz=UTC)
        except (TypeError, ValueError, OSError) as exc:
            raise ProviderUnavailableError(
                "yahoo_finance", f"Provider field '{field_name}' was invalid."
            ) from exc

    @staticmethod
    def _history(result: dict[str, Any]) -> list[HistoricalPricePoint]:
        timestamps = result.get("timestamp")
        indicators = result.get("indicators")
        quote = (
            indicators.get("quote", [{}])[0]
            if isinstance(indicators, dict)
            else None
        )
        if not isinstance(timestamps, list) or not isinstance(quote, dict):
            raise ProviderUnavailableError("yahoo_finance", "History was unavailable.")
        fields = [
            quote.get(name) for name in ("open", "high", "low", "close", "volume")
        ]
        if not all(isinstance(values, list) for values in fields):
            raise ProviderUnavailableError("yahoo_finance", "History was unavailable.")
        field_lists: list[list[Any]] = [
            values for values in fields if isinstance(values, list)
        ]
        if len(field_lists) != 5:
            raise ProviderUnavailableError("yahoo_finance", "History was unavailable.")
        points: list[HistoricalPricePoint] = []
        for index, timestamp in enumerate(timestamps):
            values = [
                field[index] if index < len(field) else None for field in field_lists
            ]
            if any(value is None for value in values):
                continue
            try:
                point_time = YahooFinanceMarketProvider._timestamp(
                    timestamp, "timestamp"
                )
                points.append(
                    HistoricalPricePoint(
                        date=point_time.date(),
                        open=YahooFinanceMarketProvider._number(values[0], "open"),
                        high=YahooFinanceMarketProvider._number(values[1], "high"),
                        low=YahooFinanceMarketProvider._number(values[2], "low"),
                        close=YahooFinanceMarketProvider._number(values[3], "close"),
                        volume=YahooFinanceMarketProvider._volume(values[4]),
                    )
                )
            except (ProviderUnavailableError, ValidationError) as exc:
                raise ProviderUnavailableError(
                    "yahoo_finance", "Provider returned invalid OHLC values."
                ) from exc
        if not points:
            raise ProviderUnavailableError("yahoo_finance", "History was unavailable.")
        return points

    async def get_history(self, ticker: str, period: str) -> list[HistoricalPricePoint]:
        result, _ = await self._chart(ticker, period)
        return self._history(result)

    async def get_quote(self, ticker: str) -> PriceSnapshot:
        normalized = ticker.strip().upper()
        result, source_url = await self._chart(normalized, "3m")
        history = self._history(result)
        meta = result.get("meta")
        if not isinstance(meta, dict):
            raise ProviderUnavailableError(self.name, "Quote metadata was unavailable.")
        latest = history[-1]
        previous = history[-2] if len(history) > 1 else None
        price = self._number(meta.get("regularMarketPrice", latest.close), "price")
        previous_close = meta.get("previousClose", meta.get("chartPreviousClose"))
        if previous_close is None and previous is not None:
            previous_close = previous.close
        previous_value = self._number(previous_close, "previous_close")
        change = price - previous_value
        try:
            open_price = self._number(
                meta.get("regularMarketOpen", latest.open), "open"
            )
            high_price = self._number(
                meta.get("regularMarketDayHigh", latest.high), "high"
            )
            low_price = self._number(meta.get("regularMarketDayLow", latest.low), "low")
            volume = self._volume(meta.get("regularMarketVolume", latest.volume))
        except (ProviderUnavailableError, ValidationError) as exc:
            raise ProviderUnavailableError(
                self.name, "Provider returned invalid quote values."
            ) from exc
        return PriceSnapshot(
            ticker=normalized,
            price=price,
            previous_close=previous_value,
            change=change,
            change_percent=change / previous_value * 100,
            open=open_price,
            high=high_price,
            low=low_price,
            volume=volume,
            currency=str(meta.get("currency", "USD")),
            as_of=self._timestamp(
                meta.get("regularMarketTime", int(datetime.now(UTC).timestamp())),
                "regularMarketTime",
            ),
            retrieved_at=datetime.now(UTC),
            source=self.name,
            source_url=source_url,
            is_delayed=True,
        )
