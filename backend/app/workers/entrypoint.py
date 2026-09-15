"""ARQ-compatible worker entry point for Linux deployment."""

import os

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.deep_research.graph import DeepResearchGraph
from app.services.market import get_market_service


async def run_deep_research(
    _ctx: dict[str, object], ticker: str, question: str
) -> None:
    await DeepResearchGraph(get_market_service()).ainvoke(ticker, question)


class WorkerSettings:
    functions = [run_deep_research]
    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", get_settings().redis_url)
    )
