from datetime import UTC, datetime

import httpx
import pytest
from pydantic import SecretStr

from app.providers.exceptions import ProviderRateLimitError
from app.providers.market_price.alpha_vantage_provider import (
    AlphaVantageMarketProvider,
)


def response_for(request: httpx.Request) -> httpx.Response:
    params = dict(request.url.params)
    if params["function"] == "GLOBAL_QUOTE":
        return httpx.Response(
            200,
            json={
                "Global Quote": {
                    "01. symbol": "NVDA",
                    "02. open": "180.00",
                    "03. high": "184.00",
                    "04. low": "179.00",
                    "05. price": "182.00",
                    "06. volume": "51300000",
                    "07. latest trading day": "2026-09-14",
                    "08. previous close": "180.00",
                    "09. change": "2.00",
                    "10. change percent": "1.1111%",
                }
            },
        )
    return httpx.Response(
        200,
        json={
            "Time Series (Daily)": {
                "2026-09-14": {
                    "1. open": "180.00",
                    "2. high": "184.00",
                    "3. low": "179.00",
                    "4. close": "182.00",
                    "5. volume": "51300000",
                },
                "2026-09-11": {
                    "1. open": "174.00",
                    "2. high": "181.00",
                    "3. low": "173.00",
                    "4. close": "180.00",
                    "5. volume": "48200000",
                },
            }
        },
    )


@pytest.mark.asyncio
async def test_alpha_vantage_maps_external_json_to_internal_schema() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(response_for))
    provider = AlphaVantageMarketProvider(SecretStr("test-key"), client=client)

    quote = await provider.get_quote("nvda")
    history = await provider.get_history("nvda", "3m")
    await client.aclose()

    assert quote.ticker == "NVDA"
    assert quote.price == 182.0
    assert quote.change_percent == pytest.approx(1.1111)
    assert quote.source == "alpha_vantage"
    assert quote.source_url is not None
    assert "apikey" not in str(quote.source_url)
    assert quote.as_of == datetime(2026, 9, 14, tzinfo=UTC)
    assert [point.date.isoformat() for point in history] == [
        "2026-09-11",
        "2026-09-14",
    ]


@pytest.mark.asyncio
async def test_alpha_vantage_maps_rate_limit_response() -> None:
    def rate_limited(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Note": "API call frequency exceeded."})

    client = httpx.AsyncClient(transport=httpx.MockTransport(rate_limited))
    provider = AlphaVantageMarketProvider(SecretStr("test-key"), client=client)

    with pytest.raises(ProviderRateLimitError):
        await provider.get_quote("NVDA")
    await client.aclose()
