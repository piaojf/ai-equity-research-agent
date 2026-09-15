from datetime import UTC, datetime

import httpx
import pytest

from app.providers.exceptions import InvalidTickerError
from app.providers.market_price.yahoo_provider import YahooFinanceMarketProvider


def _payload() -> dict[str, object]:
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": "USD",
                        "regularMarketPrice": 103.0,
                        "previousClose": 100.0,
                        "regularMarketOpen": 101.0,
                        "regularMarketDayHigh": 104.0,
                        "regularMarketDayLow": 99.0,
                        "regularMarketVolume": 1_200_000,
                        "regularMarketTime": int(
                            datetime(2026, 9, 14, tzinfo=UTC).timestamp()
                        ),
                    },
                    "timestamp": [
                        int(datetime(2026, 9, 11, tzinfo=UTC).timestamp()),
                        int(datetime(2026, 9, 14, tzinfo=UTC).timestamp()),
                    ],
                    "indicators": {
                        "quote": [
                            {
                                "open": [98.0, 101.0],
                                "high": [101.0, 104.0],
                                "low": [97.0, 99.0],
                                "close": [100.0, 103.0],
                                "volume": [900_000, 1_200_000],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }


@pytest.mark.asyncio
async def test_yahoo_provider_maps_quote_and_history() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=_payload()))
    ) as client:
        provider = YahooFinanceMarketProvider(client=client)
        quote = await provider.get_quote("nvda")
        history = await provider.get_history("NVDA", "3m")

    assert quote.ticker == "NVDA"
    assert quote.price == 103
    assert quote.change_percent == 3
    assert quote.source == "yahoo_finance"
    assert quote.is_delayed is True
    assert len(history) == 2


@pytest.mark.asyncio
async def test_yahoo_provider_rejects_invalid_payload() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, json={"chart": {"result": [], "error": None}}
            )
        )
    ) as client:
        provider = YahooFinanceMarketProvider(client=client)

        with pytest.raises(InvalidTickerError, match="not supported"):
            await provider.get_quote("UNKNOWN")
