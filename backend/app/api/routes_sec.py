from functools import lru_cache

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.request_id import get_request_id
from app.providers.exceptions import ProviderError
from app.providers.sec.edgar import SECEDGARProvider
from app.rag.embeddings import DeterministicEmbeddingProvider
from app.rag.service import SECAskResult, SECAskService
from app.rag.vector_store import InMemoryVectorStore
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/sec", tags=["sec"])


class SECAskRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    question: str = Field(min_length=1, max_length=2_000)
    filing_type: str | None = Field(default=None, max_length=16)
    limit: int = Field(default=5, ge=1, le=20)


@lru_cache(maxsize=1)
def get_sec_ask_service() -> SECAskService:
    settings = get_settings()
    provider = None
    if (
        settings.data_mode == "real"
        and settings.sec_user_agent is not None
        and settings.sec_user_agent.get_secret_value().strip()
    ):
        provider = SECEDGARProvider(
            settings.sec_user_agent,
            ticker_ciks={"NVDA": "1045810", "AMD": "2488"},
            timeout_seconds=settings.provider_timeout_seconds,
        )
    return SECAskService(
        provider=provider,
        embedder=DeterministicEmbeddingProvider(),
        vector_store=InMemoryVectorStore(),
    )


@router.post("/ask", response_model=ApiResponse[SECAskResult])
async def ask_sec(request: SECAskRequest) -> ApiResponse[SECAskResult]:
    try:
        await get_sec_ask_service().ensure_latest_filing_ingested(request.ticker)
    except ProviderError as exc:
        raise AppError(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            retryable=exc.retryable,
        ) from exc
    result = await get_sec_ask_service().ask(
        request.ticker,
        request.question,
        filing_type=request.filing_type,
        limit=request.limit,
    )
    return ApiResponse(request_id=get_request_id(), data=result)
