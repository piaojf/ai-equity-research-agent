import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.config import Settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.request_id import get_request_id
from app.providers.exceptions import ProviderError
from app.providers.fundamentals.base import FinancialDataProvider
from app.providers.fundamentals.registry import FinancialProviderRegistry
from app.schemas.financial import FinancialMetrics
from app.services.market import normalize_ticker

logger = get_logger(__name__)
T = TypeVar("T")


class FinancialService:
    def __init__(self, registry: FinancialProviderRegistry, settings: Settings) -> None:
        self.registry = registry
        self.settings = settings

    async def _call_provider(
        self,
        provider: FinancialDataProvider,
        ticker: str,
        operation_call: Callable[[], Awaitable[T]],
    ) -> T:
        for attempt in range(self.settings.provider_max_retries + 1):
            started = time.perf_counter()
            try:
                result = await operation_call()
                self._log(ticker, provider.name, "success", started)
                return result
            except ProviderError as exc:
                self._log(ticker, provider.name, "error", started, exc.code)
                if not exc.retryable or attempt >= self.settings.provider_max_retries:
                    raise AppError(
                        code=exc.code,
                        message=exc.message,
                        status_code=exc.status_code,
                        retryable=exc.retryable,
                    ) from exc
                await asyncio.sleep(
                    self.settings.provider_retry_delay_seconds * (2**attempt)
                )
        raise RuntimeError("Provider retry loop exited unexpectedly.")

    @staticmethod
    def _log(
        ticker: str,
        provider: str,
        status: str,
        started: float,
        error_code: str | None = None,
    ) -> None:
        logger.info(
            "financial_provider_request_completed",
            extra={
                "request_id": get_request_id(),
                "ticker": ticker,
                "provider": provider,
                "status": status,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "error_code": error_code,
            },
        )

    async def get_financials(self, ticker: str) -> FinancialMetrics:
        normalized = normalize_ticker(ticker)
        try:
            provider = self.registry.get_provider()
        except ProviderError as exc:
            raise AppError(
                code=exc.code,
                message=exc.message,
                status_code=exc.status_code,
                retryable=exc.retryable,
            ) from exc
        return await self._call_provider(
            provider,
            normalized,
            lambda: provider.get_financials(normalized),
        )


def get_financial_service() -> FinancialService:
    from app.core.config import get_settings

    settings = get_settings()
    return FinancialService(FinancialProviderRegistry(settings), settings)
