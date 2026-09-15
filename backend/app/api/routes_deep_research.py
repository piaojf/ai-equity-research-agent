from functools import lru_cache
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.request_id import get_request_id
from app.deep_research.graph import DeepResearchGraph
from app.schemas.common import ApiResponse
from app.schemas.deep_research import (
    DeepResearchAccepted,
    DeepResearchRequest,
    DeepResearchTaskStatus,
)
from app.services.market import get_market_service
from app.workers.queue import InMemoryTaskQueue
from app.workers.service import DeepResearchService

router = APIRouter(prefix="/api/deep-research", tags=["deep-research"])


@lru_cache(maxsize=1)
def get_deep_research_service() -> DeepResearchService:
    return DeepResearchService(
        InMemoryTaskQueue(),
        DeepResearchGraph(get_market_service()),
    )


@router.post("", response_model=ApiResponse[DeepResearchAccepted], status_code=202)
async def submit_deep_research(
    request: DeepResearchRequest,
) -> ApiResponse[DeepResearchAccepted]:
    accepted = await get_deep_research_service().submit(
        request.ticker, request.question
    )
    return ApiResponse(request_id=get_request_id(), data=accepted)


@router.get("/{task_id}", response_model=ApiResponse[DeepResearchTaskStatus])
async def get_deep_research_status(
    task_id: UUID,
) -> ApiResponse[DeepResearchTaskStatus]:
    status = get_deep_research_service().status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Deep research task not found.")
    return ApiResponse(request_id=get_request_id(), data=status)
