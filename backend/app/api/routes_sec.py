from functools import lru_cache

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.request_id import get_request_id
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
    return SECAskService(
        provider=None,
        embedder=DeterministicEmbeddingProvider(),
        vector_store=InMemoryVectorStore(),
    )


@router.post("/ask", response_model=ApiResponse[SECAskResult])
async def ask_sec(request: SECAskRequest) -> ApiResponse[SECAskResult]:
    result = await get_sec_ask_service().ask(
        request.ticker,
        request.question,
        filing_type=request.filing_type,
        limit=request.limit,
    )
    return ApiResponse(request_id=get_request_id(), data=result)
