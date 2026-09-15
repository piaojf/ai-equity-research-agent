from app.core.config import Settings
from app.providers.exceptions import ProviderConfigurationError
from app.providers.fundamentals.base import FinancialDataProvider
from app.providers.fundamentals.mock_provider import MockFinancialDataProvider
from app.providers.fundamentals.sec_company_facts import SECCompanyFactsProvider


class FinancialProviderRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_provider(self) -> FinancialDataProvider:
        if self.settings.data_mode == "mock":
            return MockFinancialDataProvider()
        if self.settings.sec_user_agent is None:
            if self.settings.data_mode == "hybrid":
                return MockFinancialDataProvider()
            raise ProviderConfigurationError("SEC_USER_AGENT is required.")
        return SECCompanyFactsProvider(
            user_agent=self.settings.sec_user_agent,
            timeout_seconds=self.settings.provider_timeout_seconds,
        )
