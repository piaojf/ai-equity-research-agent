from functools import lru_cache

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.request_id import get_request_id
from app.providers.exceptions import ProviderError
from app.providers.llm.openai_compatible import OpenAICompatibleProvider
from app.providers.sec.edgar import SECEDGARProvider
from app.rag.embeddings import DeterministicEmbeddingProvider
from app.rag.service import SECAskResult, SECAskService, StructuredSECAskLLM
from app.rag.vector_store import InMemoryVectorStore, QdrantVectorStore, VectorStore
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
            timeout_seconds=settings.sec_provider_timeout_seconds,
        )
    embedder = DeterministicEmbeddingProvider()
    vector_store: VectorStore
    if settings.data_mode == "real":
        vector_store = QdrantVectorStore(
            settings.qdrant_url,
            collection=settings.qdrant_collection,
            dimension=embedder.dimension,
        )
    else:
        vector_store = InMemoryVectorStore()
    answerer = None
    if (
        settings.deepseek_api_key is not None
        and settings.deepseek_api_key.get_secret_value().strip()
    ):
        answerer = StructuredSECAskLLM(
            OpenAICompatibleProvider(
                settings.deepseek_api_key,
                model=settings.deepseek_model,
                base_url=settings.deepseek_base_url,
                timeout_seconds=settings.provider_timeout_seconds * 3,
            )
        )
    return SECAskService(
        provider=provider,
        embedder=embedder,
        vector_store=vector_store,
        answerer=answerer,
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
    try:
        result = await get_sec_ask_service().ask(
            request.ticker,
            request.question,
            filing_type=request.filing_type,
            limit=request.limit,
        )
    except AppError:
        raise
    except Exception as exc:
        raise AppError(
            code=(
                ErrorCode.QDRANT_ERROR
                if get_settings().data_mode == "real"
                else ErrorCode.INTERNAL_ERROR
            ),
            message="SEC evidence retrieval or synthesis failed.",
            status_code=503,
            retryable=True,
        ) from exc
    return ApiResponse(request_id=get_request_id(), data=result)
