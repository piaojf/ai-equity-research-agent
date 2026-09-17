import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.providers.exceptions import ProviderConfigurationError
from app.providers.market_price.alpha_vantage_provider import (
    AlphaVantageMarketProvider,
)
from app.providers.market_price.mock_provider import MockMarketProvider
from app.providers.market_price.registry import MarketProviderRegistry
from app.providers.market_price.yahoo_provider import YahooFinanceMarketProvider


def test_mock_mode_selects_mock_provider() -> None:
    provider = MarketProviderRegistry(Settings(data_mode="mock")).get_provider()

    assert isinstance(provider, MockMarketProvider)


def test_real_mode_without_key_raises_configuration_error() -> None:
    registry = MarketProviderRegistry(
        Settings(data_mode="real", market_provider="alpha_vantage")
    )

    with pytest.raises(ProviderConfigurationError, match="API_KEY"):
        registry.get_provider()


def test_hybrid_mode_without_key_explicitly_selects_mock() -> None:
    provider = MarketProviderRegistry(Settings(data_mode="hybrid")).get_provider()

    assert isinstance(provider, MockMarketProvider)
    assert provider.name == "mock"


def test_real_mode_with_key_selects_alpha_vantage() -> None:
    settings = Settings(
        data_mode="real",
        market_provider="alpha_vantage",
        alpha_vantage_api_key=SecretStr("test-key"),
    )

    provider = MarketProviderRegistry(settings).get_provider()

    assert isinstance(provider, AlphaVantageMarketProvider)


def test_real_mode_defaults_to_keyless_yahoo_provider() -> None:
    provider = MarketProviderRegistry(Settings(data_mode="real")).get_provider()

    assert isinstance(provider, YahooFinanceMarketProvider)


def test_real_mode_yahoo_provider_uses_configured_proxy() -> None:
    settings = Settings(
        data_mode="real",
        yahoo_proxy_url="http://127.0.0.1:10811",
    )

    provider = MarketProviderRegistry(settings).get_provider()

    assert isinstance(provider, YahooFinanceMarketProvider)
    assert provider.proxy_url == "http://127.0.0.1:10811"
