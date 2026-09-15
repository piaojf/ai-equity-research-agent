from datetime import datetime

import pytest

from app.providers.exceptions import InvalidTickerError
from app.providers.market_price.base import MarketDataProvider
from app.providers.market_price.mock_provider import MockMarketProvider

SUPPORTED_TICKERS = ["NVDA", "AAPL", "MSFT", "TSLA", "AMD"]


@pytest.mark.asyncio
@pytest.mark.parametrize("ticker", SUPPORTED_TICKERS)
async def test_market_provider_contract(ticker: str) -> None:
    provider: MarketDataProvider = MockMarketProvider()

    quote = await provider.get_quote(ticker)
    history = await provider.get_history(ticker, "3m")

    assert quote.ticker == ticker
    assert quote.price > 0
    assert quote.source
    assert quote.retrieved_at is not None
    assert history
    assert history == sorted(history, key=lambda point: point.date)
    assert all(point.high >= point.low for point in history)
    assert all(point.volume >= 0 for point in history)
    assert isinstance(quote.as_of, datetime)
    assert quote.source == "mock"


@pytest.mark.asyncio
async def test_mock_provider_is_deterministic() -> None:
    provider = MockMarketProvider()

    first = await provider.get_quote("NVDA")
    second = await provider.get_quote("NVDA")

    assert first == second


@pytest.mark.asyncio
async def test_mock_provider_rejects_unknown_ticker() -> None:
    provider = MockMarketProvider()

    with pytest.raises(InvalidTickerError, match="not supported"):
        await provider.get_quote("UNKNOWN")
