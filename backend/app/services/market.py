import asyncio
import re
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.core.request_id import get_request_id
from app.providers.exceptions import ProviderError
from app.providers.market_price.base import MarketDataProvider
from app.providers.market_price.registry import MarketProviderRegistry
from app.schemas.market import MarketHistory, StockOverview, date_as_utc

logger = get_logger(__name__)
T = TypeVar("T")
_TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
_PERIOD = "3m"


def normalize_ticker(ticker: str) -> str:
    normalized = ticker.strip().upper()
    if not _TICKER_PATTERN.fullmatch(normalized):
        raise AppError(
            code=ErrorCode.INVALID_TICKER,
            message="Ticker must contain 1-10 letters, digits, dots, or hyphens.",
            status_code=400,
        )
    return normalized


class MarketService:
    def __init__(self, registry: MarketProviderRegistry, settings: Settings) -> None:
        self.registry = registry
        self.settings = settings

    async def _call_provider(
        self,
        provider: MarketDataProvider,
        operation: str,
        ticker: str,
        operation_call: Callable[[], Awaitable[T]],
    ) -> T:
        for attempt in range(self.settings.provider_max_retries + 1):
            started = time.perf_counter()
            try:
                result = await operation_call()
                self._log_provider(
                    ticker=ticker,
                    provider=provider.name,
                    operation=operation,
                    latency_ms=self._latency(started),
                    status="success",
                )
                return result
            except ProviderError as exc:
                self._log_provider(
                    ticker=ticker,
                    provider=provider.name,
                    operation=operation,
                    latency_ms=self._latency(started),
                    status="error",
                    error_code=exc.code,
                )
                if not exc.retryable or attempt >= self.settings.provider_max_retries:
                    raise self._to_app_error(exc) from exc
                delay = self.settings.provider_retry_delay_seconds * (2**attempt)
                await asyncio.sleep(delay)
        raise RuntimeError("Provider retry loop exited unexpectedly.")

    @staticmethod
    def _latency(started: float) -> float:
        return round((time.perf_counter() - started) * 1000, 2)

    @staticmethod
    def _to_app_error(exc: ProviderError) -> AppError:
        return AppError(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            retryable=exc.retryable,
        )

    @staticmethod
    def _log_provider(
        *,
        ticker: str,
        provider: str,
        operation: str,
        latency_ms: float,
        status: str,
        error_code: str | None = None,
    ) -> None:
        logger.info(
            "provider_request_completed",
            extra={
                "request_id": get_request_id(),
                "ticker": ticker,
                "provider": provider,
                "operation": operation,
                "latency_ms": latency_ms,
                "status": status,
                "error_code": error_code,
            },
        )

    async def get_stock_overview(self, ticker: str) -> StockOverview:
        normalized = normalize_ticker(ticker)
        try:
            provider = self.registry.get_provider()
        except ProviderError as exc:
            raise self._to_app_error(exc) from exc
        quote = await self._call_provider(
            provider,
            "get_quote",
            normalized,
            lambda: provider.get_quote(normalized),
        )
        points = await self._call_provider(
            provider,
            "get_history",
            normalized,
            lambda: provider.get_history(normalized, _PERIOD),
        )
        if not points:
            raise AppError(
                code=ErrorCode.MARKET_DATA_UNAVAILABLE,
                message="Market history is unavailable.",
                status_code=503,
            )
        retrieved_at = quote.retrieved_at
        as_of = date_as_utc(points[-1].date)
        history = MarketHistory(
            ticker=normalized,
            period=_PERIOD,
            points=points,
            source=provider.name,
            source_url=provider.source_url,
            as_of=as_of,
            retrieved_at=retrieved_at,
            is_delayed=quote.is_delayed,
        )
        return StockOverview(ticker=normalized, quote=quote, history=history)


def get_market_service() -> MarketService:
    from app.core.config import get_settings

    settings = get_settings()
    return MarketService(MarketProviderRegistry(settings), settings)
