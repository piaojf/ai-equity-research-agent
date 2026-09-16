import asyncio
from functools import lru_cache
from uuid import UUID

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.request_id import get_request_id
from app.db.session import Database
from app.deep_research.graph import DeepResearchGraph
from app.schemas.common import ApiResponse
from app.schemas.deep_research import (
    DeepResearchAccepted,
    DeepResearchRequest,
    DeepResearchTaskStatus,
)
from app.services.market import get_market_service
from app.workers.queue import InMemoryTaskQueue, RedisTaskQueue
from app.workers.service import DeepResearchService, DurableDeepResearchService

router = APIRouter(prefix="/api/deep-research", tags=["deep-research"])


@lru_cache(maxsize=1)
def get_in_memory_service() -> DeepResearchService:
    return DeepResearchService(
        InMemoryTaskQueue(),
        DeepResearchGraph(get_market_service()),
    )


_durable_database: Database | None = None
_durable_pool: ArqRedis | None = None
_durable_service: DurableDeepResearchService | None = None
_durable_lock = asyncio.Lock()


async def get_durable_service() -> DurableDeepResearchService:
    global _durable_database, _durable_pool, _durable_service
    if _durable_service is not None:
        return _durable_service
    async with _durable_lock:
        if _durable_service is None:
            settings = get_settings()
            try:
                _durable_database = Database(settings.database_url)
                await _durable_database.create_schema()
                _durable_pool = await create_pool(
                    RedisSettings.from_dsn(settings.redis_url)
                )
                _durable_service = DurableDeepResearchService(
                    _durable_database,
                    RedisTaskQueue(_durable_pool),
                )
            except Exception as exc:
                await close_durable_service()
                raise HTTPException(
                    status_code=503,
                    detail="Research persistence or queue is unavailable.",
                ) from exc
    return _durable_service


async def close_durable_service() -> None:
    global _durable_database, _durable_pool, _durable_service
    if _durable_pool is not None:
        _durable_pool.close()
    if _durable_database is not None:
        await _durable_database.dispose()
    _durable_database = None
    _durable_pool = None
    _durable_service = None


def _uses_durable_runtime() -> bool:
    return get_settings().data_mode == "real"




@router.post("", response_model=ApiResponse[DeepResearchAccepted], status_code=202)
async def submit_deep_research(
    request: DeepResearchRequest,
) -> ApiResponse[DeepResearchAccepted]:
    if _uses_durable_runtime():
        accepted = await (await get_durable_service()).submit(
            request.ticker,
            request.question,
            request_id=get_request_id(),
        )
    else:
        service = get_in_memory_service()
        accepted = await service.submit(request.ticker, request.question)
        asyncio.create_task(service.run_once())
    return ApiResponse(request_id=get_request_id(), data=accepted)


@router.get("/{task_id}", response_model=ApiResponse[DeepResearchTaskStatus])
async def get_deep_research_status(
    task_id: UUID,
) -> ApiResponse[DeepResearchTaskStatus]:
    if _uses_durable_runtime():
        status = await (await get_durable_service()).status(task_id)
    else:
        status = get_in_memory_service().status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Deep research task not found.")
    return ApiResponse(request_id=get_request_id(), data=status)
