from collections.abc import Callable

import pytest

from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.providers.exceptions import ProviderUnavailableError
from app.providers.fundamentals.base import FinancialDataProvider
from app.providers.fundamentals.registry import FinancialProviderRegistry
from app.schemas.financial import FinancialMetrics
from app.services.financial import FinancialService


class StubRegistry(FinancialProviderRegistry):
    def __init__(self, provider: FinancialDataProvider) -> None:
        self.provider = provider

    def get_provider(self) -> FinancialDataProvider:
        return self.provider


class StubProvider:
    name = "stub_financials"

    def __init__(self, call: Callable[[str], FinancialMetrics]) -> None:
        self.call = call

    async def get_financials(self, ticker: str) -> FinancialMetrics:
        return self.call(ticker)


def metrics(ticker: str) -> FinancialMetrics:
    return FinancialMetrics(ticker=ticker)


@pytest.mark.asyncio
async def test_financial_service_normalizes_ticker() -> None:
    settings = Settings(provider_retry_delay_seconds=0)
    service = FinancialService(
        StubRegistry(StubProvider(metrics)),
        settings,
    )

    result = await service.get_financials(" nvda ")

    assert result.ticker == "NVDA"


@pytest.mark.asyncio
async def test_financial_service_maps_provider_errors() -> None:
    def fail(_: str) -> FinancialMetrics:
        raise ProviderUnavailableError("stub", "financial data unavailable")

    service = FinancialService(
        StubRegistry(StubProvider(fail)),
        Settings(provider_retry_delay_seconds=0, provider_max_retries=0),
    )

    with pytest.raises(AppError) as raised:
        await service.get_financials("NVDA")

    assert raised.value.code == ErrorCode.MARKET_DATA_UNAVAILABLE
    assert raised.value.status_code == 503


def test_financial_registry_uses_mock_without_keys() -> None:
    provider = FinancialProviderRegistry(Settings(data_mode="mock")).get_provider()

    assert provider.name == "mock_financials"
