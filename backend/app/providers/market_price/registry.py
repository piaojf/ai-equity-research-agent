from app.core.config import Settings
from app.providers.exceptions import ProviderConfigurationError
from app.providers.market_price.alpha_vantage_provider import AlphaVantageMarketProvider
from app.providers.market_price.base import MarketDataProvider
from app.providers.market_price.mock_provider import MockMarketProvider
from app.providers.market_price.yahoo_provider import YahooFinanceMarketProvider


class MarketProviderRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_provider(self) -> MarketDataProvider:
        if self.settings.data_mode == "mock":
            return MockMarketProvider()
        if self.settings.data_mode == "hybrid":
            if (
                self.settings.market_provider == "yahoo"
                or self.settings.alpha_vantage_api_key is None
            ):
                return MockMarketProvider()
        if self.settings.market_provider == "yahoo":
            return YahooFinanceMarketProvider(
                timeout_seconds=self.settings.provider_timeout_seconds,
                proxy_url=self.settings.yahoo_proxy_url,
            )
        if self.settings.market_provider != "alpha_vantage":
            raise ProviderConfigurationError(
                f"Unsupported market provider: {self.settings.market_provider}."
            )
        if self.settings.alpha_vantage_api_key is None:
            if self.settings.data_mode == "hybrid":
                return MockMarketProvider()
            raise ProviderConfigurationError("ALPHA_VANTAGE_API_KEY is required.")
        return AlphaVantageMarketProvider(
            api_key=self.settings.alpha_vantage_api_key,
            timeout_seconds=self.settings.provider_timeout_seconds,
        )
