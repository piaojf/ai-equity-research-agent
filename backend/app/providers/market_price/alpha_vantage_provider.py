from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import HttpUrl, SecretStr, TypeAdapter, ValidationError

from app.providers.exceptions import (
    InvalidTickerError,
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.market_price.base import MarketDataProvider
from app.schemas.market import HistoricalPricePoint, PriceSnapshot


class AlphaVantageMarketProvider(MarketDataProvider):
    name = "alpha_vantage"
    base_url = "https://www.alphavantage.co/query"
    source_url: HttpUrl = TypeAdapter(HttpUrl).validate_python(base_url)

    def __init__(
        self,
        api_key: SecretStr | str | None,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if api_key is None or (
            isinstance(api_key, SecretStr) and not api_key.get_secret_value()
        ) or (isinstance(api_key, str) and not api_key):
            raise ProviderConfigurationError("ALPHA_VANTAGE_API_KEY is required.")
        self.api_key = (
            api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key
        )
        self.timeout_seconds = timeout_seconds
        self._client = client

    def _public_source_url(self, function: str, ticker: str) -> HttpUrl:
        return TypeAdapter(HttpUrl).validate_python(
            f"{self.base_url}?function={function}&symbol={ticker}"
        )

    async def _request(self, function: str, ticker: str) -> dict[str, Any]:
        params = {"function": function, "symbol": ticker, "apikey": self.api_key}
        try:
            if self._client is not None:
                response = await self._client.get(self.base_url, params=params)
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.get(self.base_url, params=params)
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
                self.name,
                "Provider returned invalid JSON.",
            ) from exc

        if not isinstance(payload, dict):
            raise ProviderUnavailableError(
                self.name,
                "Provider returned an invalid payload.",
            )
        if "Note" in payload or "Information" in payload:
            raise ProviderRateLimitError(self.name)
        return payload

    @staticmethod
    def _number(value: Any, field_name: str) -> float:
        try:
            return float(str(value).replace("%", "").strip())
        except (TypeError, ValueError) as exc:
            raise ProviderUnavailableError(
                "alpha_vantage",
                f"Provider field '{field_name}' was not numeric.",
            ) from exc

    async def get_quote(self, ticker: str) -> PriceSnapshot:
        normalized = ticker.strip().upper()
        payload = await self._request("GLOBAL_QUOTE", normalized)
        raw = payload.get("Global Quote")
        if not isinstance(raw, dict) or not raw.get("05. price"):
            raise InvalidTickerError(normalized)
        trading_day = raw.get("07. latest trading day")
        try:
            as_of_date = datetime.strptime(str(trading_day), "%Y-%m-%d").date()
        except ValueError as exc:
            raise ProviderUnavailableError(
                self.name,
                "Provider returned an invalid trading date.",
            ) from exc
        as_of = datetime(as_of_date.year, as_of_date.month, as_of_date.day, tzinfo=UTC)
        previous_close = self._number(raw.get("08. previous close"), "previous_close")
        change = self._number(raw.get("09. change"), "change")
        try:
            return PriceSnapshot(
                ticker=normalized,
                price=self._number(raw.get("05. price"), "price"),
                previous_close=previous_close,
                change=change,
                change_percent=self._number(
                    raw.get("10. change percent"),
                    "change_percent",
                ),
                open=self._number(raw.get("02. open"), "open"),
                high=self._number(raw.get("03. high"), "high"),
                low=self._number(raw.get("04. low"), "low"),
                volume=int(self._number(raw.get("06. volume"), "volume")),
                currency="USD",
                as_of=as_of,
                retrieved_at=datetime.now(UTC),
                source=self.name,
                source_url=self._public_source_url("GLOBAL_QUOTE", normalized),
                is_delayed=True,
            )
        except ValidationError as exc:
            raise ProviderUnavailableError(
                self.name,
                "Provider returned invalid quote values.",
            ) from exc

    async def get_history(
        self,
        ticker: str,
        period: str,
    ) -> list[HistoricalPricePoint]:
        normalized = ticker.strip().upper()
        payload = await self._request("TIME_SERIES_DAILY", normalized)
        raw_series = payload.get("Time Series (Daily)")
        if not isinstance(raw_series, dict) or not raw_series:
            raise InvalidTickerError(normalized)
        points: list[HistoricalPricePoint] = []
        for raw_date, values in raw_series.items():
            if not isinstance(values, dict):
                raise ProviderUnavailableError(
                    self.name,
                    "Provider returned invalid OHLC data.",
                )
            try:
                parsed_date = datetime.strptime(str(raw_date), "%Y-%m-%d").date()
                points.append(
                    HistoricalPricePoint(
                        date=parsed_date,
                        open=self._number(values.get("1. open"), "open"),
                        high=self._number(values.get("2. high"), "high"),
                        low=self._number(values.get("3. low"), "low"),
                        close=self._number(values.get("4. close"), "close"),
                        volume=int(self._number(values.get("5. volume"), "volume")),
                    )
                )
            except (ValueError, ValidationError) as exc:
                raise ProviderUnavailableError(
                    self.name,
                    "Provider returned invalid OHLC values.",
                ) from exc
        points.sort(key=lambda point: point.date)
        limits = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
        limit = limits.get(period)
        return points[-limit:] if limit is not None else points
