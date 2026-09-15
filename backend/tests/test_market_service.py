from collections.abc import Callable
from datetime import UTC, date, datetime

import pytest

from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.providers.exceptions import (
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.market_price.base import MarketDataProvider
from app.providers.market_price.registry import MarketProviderRegistry
from app.schemas.market import HistoricalPricePoint, PriceSnapshot
from app.services.market import MarketService, normalize_ticker


def make_provider(
    quote_call: Callable[[], PriceSnapshot] | None = None,
    history_call: Callable[[], list[HistoricalPricePoint]] | None = None,
) -> MarketDataProvider:
    class StubProvider:
        name = "stub"
        source_url = None

        async def get_quote(self, ticker: str) -> PriceSnapshot:
            del ticker
            if quote_call is not None:
                return quote_call()
            return PriceSnapshot(
                ticker="NVDA",
                price=182,
                previous_close=180,
                change=2,
                change_percent=1.11,
                open=180,
                high=184,
                low=179,
                volume=100,
                currency="USD",
                as_of=datetime(2026, 9, 14, tzinfo=UTC),
                retrieved_at=datetime(2026, 9, 14, 20, tzinfo=UTC),
                source="stub",
                is_delayed=True,
            )

        async def get_history(
            self,
            ticker: str,
            period: str,
        ) -> list[HistoricalPricePoint]:
            del ticker, period
            if history_call is not None:
                return history_call()
            return [
                HistoricalPricePoint(
                    date=date(2026, 9, 14),
                    open=180,
                    high=184,
                    low=179,
                    close=182,
                    volume=100,
                )
            ]

    return StubProvider()


class StubRegistry(MarketProviderRegistry):
    def __init__(self, provider: MarketDataProvider) -> None:
        self.provider = provider

    def get_provider(self) -> MarketDataProvider:
        return self.provider


@pytest.mark.asyncio
async def test_service_normalizes_ticker_and_wraps_history() -> None:
    settings = Settings(provider_retry_delay_seconds=0)
    service = MarketService(StubRegistry(make_provider()), settings)

    result = await service.get_stock_overview(" nvda ")

    assert result.ticker == "NVDA"
    assert result.quote.ticker == "NVDA"
    assert result.history.ticker == "NVDA"
    assert result.history.source == "stub"


def test_normalize_ticker_rejects_invalid_value() -> None:
    with pytest.raises(AppError) as raised:
        normalize_ticker("not a ticker")

    assert raised.value.code == ErrorCode.INVALID_TICKER
    assert raised.value.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider_error",
    [ProviderTimeoutError("stub"), ProviderRateLimitError("stub")],
)
async def test_service_retries_retryable_provider_errors(
    provider_error: Exception,
) -> None:
    attempts = 0

    def quote() -> PriceSnapshot:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise provider_error
        return PriceSnapshot(
            ticker="NVDA",
            price=182,
            previous_close=180,
            change=2,
            change_percent=1.11,
            open=180,
            high=184,
            low=179,
            volume=100,
            currency="USD",
            as_of=datetime(2026, 9, 14, tzinfo=UTC),
            retrieved_at=datetime(2026, 9, 14, 20, tzinfo=UTC),
            source="stub",
            is_delayed=True,
        )

    settings = Settings(provider_retry_delay_seconds=0, provider_max_retries=2)
    service = MarketService(StubRegistry(make_provider(quote_call=quote)), settings)

    result = await service.get_stock_overview("NVDA")

    assert result.quote.price == 182
    assert attempts == 3


@pytest.mark.asyncio
async def test_service_maps_unavailable_provider_after_retries() -> None:
    settings = Settings(provider_retry_delay_seconds=0, provider_max_retries=1)
    service = MarketService(
        StubRegistry(
            make_provider(
                quote_call=lambda: (_ for _ in ()).throw(
                    ProviderUnavailableError("stub")
                )
            )
        ),
        settings,
    )

    with pytest.raises(AppError) as raised:
        await service.get_stock_overview("NVDA")

    assert raised.value.code == ErrorCode.MARKET_DATA_UNAVAILABLE
    assert raised.value.status_code == 503
