import json
import time
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.request_id import get_request_id
from app.schemas.market import StockSearchItem

logger = get_logger(__name__)

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_CACHE_TTL_SECONDS = 24 * 60 * 60
_SEED_ITEMS = (
    StockSearchItem(ticker="AAPL", company_name="Apple Inc."),
    StockSearchItem(ticker="AMD", company_name="Advanced Micro Devices, Inc."),
    StockSearchItem(ticker="AMZN", company_name="Amazon.com, Inc."),
    StockSearchItem(ticker="AVGO", company_name="Broadcom Inc."),
    StockSearchItem(ticker="GOOG", company_name="Alphabet Inc."),
    StockSearchItem(ticker="GOOGL", company_name="Alphabet Inc."),
    StockSearchItem(ticker="INTC", company_name="Intel Corporation"),
    StockSearchItem(ticker="META", company_name="Meta Platforms, Inc."),
    StockSearchItem(ticker="MSFT", company_name="Microsoft Corporation"),
    StockSearchItem(ticker="NVDA", company_name="NVIDIA Corporation"),
    StockSearchItem(ticker="TSLA", company_name="Tesla, Inc."),
)


class StockUniverseService:
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
        cache_path: Path | None = None,
    ) -> None:
        self.settings = settings
        self.client = client
        self.cache_path = cache_path or (
            Path(__file__).resolve().parents[3]
            / "work"
            / "cache"
            / "us_stock_universe.json"
        )

    async def search(self, query: str, limit: int = 10) -> list[StockSearchItem]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        items = await self._load_items()
        query_ticker = normalized_query.upper()
        query_name = normalized_query.casefold()
        ranked = sorted(
            (
                (self._rank(item, query_ticker, query_name), item)
                for item in items
                if self._matches(item, query_ticker, query_name)
            ),
            key=lambda pair: (pair[0], pair[1].ticker),
        )
        return [item for _, item in ranked[:limit]]

    async def _load_items(self) -> list[StockSearchItem]:
        if self.settings.data_mode == "mock":
            return list(_SEED_ITEMS)

        cached_items = self._read_cache()
        if cached_items is not None:
            return cached_items

        user_agent = self._user_agent()
        if not user_agent:
            self._log_fallback("sec_user_agent_not_configured")
            return list(_SEED_ITEMS)

        try:
            payload = await self._fetch_sec_directory(user_agent)
            items = self._parse_sec_payload(payload)
            if not items:
                raise ValueError("SEC ticker directory was empty")
            self._write_cache(items)
            return items
        except (httpx.HTTPError, OSError, ValueError) as exc:
            self._log_fallback(type(exc).__name__)
            return list(_SEED_ITEMS)

    async def _fetch_sec_directory(self, user_agent: str) -> Any:
        headers = {"Accept": "application/json", "User-Agent": user_agent}
        if self.client is not None:
            response = await self.client.get(SEC_TICKERS_URL, headers=headers)
            response.raise_for_status()
            return response.json()

        async with httpx.AsyncClient(
            timeout=self.settings.sec_provider_timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = await client.get(SEC_TICKERS_URL, headers=headers)
            response.raise_for_status()
            return response.json()

    def _read_cache(self) -> list[StockSearchItem] | None:
        try:
            if not self.cache_path.is_file():
                return None
            if time.time() - self.cache_path.stat().st_mtime > _CACHE_TTL_SECONDS:
                return None
            raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return None
            return self._parse_items(raw.get("items"))
        except (OSError, TypeError, ValueError):
            return None

    def _write_cache(self, items: list[StockSearchItem]) -> None:
        payload = {
            "source": SEC_TICKERS_URL,
            "items": [item.model_dump(mode="json") for item in items],
        }
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    @staticmethod
    def _parse_items(raw_items: Any) -> list[StockSearchItem] | None:
        if not isinstance(raw_items, list):
            return None
        items: list[StockSearchItem] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            ticker = raw_item.get("ticker")
            company_name = raw_item.get("company_name")
            if (
                isinstance(ticker, str)
                and isinstance(company_name, str)
                and ticker
                and company_name
            ):
                exchange = raw_item.get("exchange")
                items.append(
                    StockSearchItem(
                        ticker=ticker.upper(),
                        company_name=company_name,
                        exchange=exchange if isinstance(exchange, str) else None,
                    )
                )
        return items or None

    @classmethod
    def _parse_sec_payload(cls, payload: Any) -> list[StockSearchItem]:
        if not isinstance(payload, dict):
            raise ValueError("SEC ticker directory has an invalid shape")
        items: list[StockSearchItem] = []
        seen: set[str] = set()
        for raw_item in payload.values():
            if not isinstance(raw_item, dict):
                continue
            ticker = raw_item.get("ticker")
            title = raw_item.get("title")
            if not isinstance(ticker, str) or not isinstance(title, str):
                continue
            normalized_ticker = ticker.strip().upper()
            normalized_title = " ".join(title.split())
            if (
                not normalized_ticker
                or not normalized_title
                or normalized_ticker in seen
            ):
                continue
            seen.add(normalized_ticker)
            items.append(
                StockSearchItem(
                    ticker=normalized_ticker,
                    company_name=normalized_title,
                )
            )
        return items

    @staticmethod
    def _matches(item: StockSearchItem, query_ticker: str, query_name: str) -> bool:
        return query_ticker in item.ticker or query_name in item.company_name.casefold()

    @staticmethod
    def _rank(item: StockSearchItem, query_ticker: str, query_name: str) -> int:
        if item.ticker == query_ticker:
            return 0
        if item.ticker.startswith(query_ticker):
            return 1
        company_name = item.company_name.casefold()
        if company_name.split(" ", 1)[0] == query_name:
            return 2
        if company_name.startswith(query_name):
            return 3
        if query_ticker in item.ticker:
            return 4
        return 4

    @staticmethod
    def _user_agent_from_settings(settings: Settings) -> str | None:
        if settings.sec_user_agent is None:
            return None
        return settings.sec_user_agent.get_secret_value().strip() or None

    def _user_agent(self) -> str | None:
        return self._user_agent_from_settings(self.settings)

    @staticmethod
    def _log_fallback(reason: str) -> None:
        logger.warning(
            "stock_universe_fallback",
            extra={"request_id": get_request_id(), "reason": reason},
        )


def get_stock_universe_service() -> StockUniverseService:
    from app.core.config import get_settings

    return StockUniverseService(get_settings())
