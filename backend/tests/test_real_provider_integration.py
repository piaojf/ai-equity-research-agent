import os

import pytest

from app.core.config import Settings
from app.providers.market_price.alpha_vantage_provider import (
    AlphaVantageMarketProvider,
)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("RUN_REAL_PROVIDER_TESTS")
    or not os.getenv("ALPHA_VANTAGE_API_KEY"),
    reason="Set RUN_REAL_PROVIDER_TESTS=1 and ALPHA_VANTAGE_API_KEY to enable.",
)
async def test_alpha_vantage_real_provider_contract() -> None:
    settings = Settings(
        data_mode="real",
        alpha_vantage_api_key=os.environ["ALPHA_VANTAGE_API_KEY"],
    )
    provider = AlphaVantageMarketProvider(
        api_key=settings.alpha_vantage_api_key,
        timeout_seconds=settings.provider_timeout_seconds,
    )

    quote = await provider.get_quote("IBM")
    history = await provider.get_history("IBM", "1m")

    assert quote.ticker == "IBM"
    assert quote.price > 0
    assert quote.source == "alpha_vantage"
    assert quote.retrieved_at is not None
    assert history
