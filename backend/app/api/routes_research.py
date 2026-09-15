from functools import lru_cache

from fastapi import APIRouter

from app.agents.research import ResearchGraph, build_research_graph
from app.core.config import get_settings
from app.core.request_id import get_request_id
from app.providers.llm.openai_compatible import OpenAICompatibleProvider
from app.schemas.common import ApiResponse
from app.schemas.research import EquityResearchReport, ResearchRequest
from app.scoring.service import ScoringService
from app.services.financial import get_financial_service
from app.services.market import get_market_service
from app.tools.research import (
    LLMReportInterpreter,
    MockReportInterpreter,
    ReportInterpreter,
)

router = APIRouter(prefix="/api/research", tags=["research"])


@lru_cache(maxsize=1)
def get_research_graph() -> ResearchGraph:
    settings = get_settings()
    interpreter: ReportInterpreter = MockReportInterpreter()
    if (
        settings.deepseek_api_key is not None
        and settings.deepseek_api_key.get_secret_value().strip()
    ):
        interpreter = LLMReportInterpreter(
            OpenAICompatibleProvider(
                settings.deepseek_api_key,
                model=settings.deepseek_model,
                base_url=settings.deepseek_base_url,
                timeout_seconds=settings.provider_timeout_seconds * 3,
            )
        )
    elif (
        settings.openai_api_key is not None
        and settings.openai_api_key.get_secret_value().strip()
    ):
        interpreter = LLMReportInterpreter(
            OpenAICompatibleProvider(
                settings.openai_api_key,
                model=settings.openai_model,
                base_url=settings.openai_base_url,
                timeout_seconds=settings.provider_timeout_seconds * 3,
            )
        )
    return build_research_graph(
        get_market_service(),
        get_financial_service(),
        ScoringService(),
        interpreter=interpreter,
    )


async def _run(request: ResearchRequest) -> ApiResponse[EquityResearchReport]:
    report = await get_research_graph().ainvoke(
        request.ticker,
        question=request.question,
        include_sec_research=request.include_sec_research,
    )
    return ApiResponse(request_id=get_request_id(), data=report)


@router.post("", response_model=ApiResponse[EquityResearchReport])
async def create_research(
    request: ResearchRequest,
) -> ApiResponse[EquityResearchReport]:
    return await _run(request)


@router.get("/{ticker}", response_model=ApiResponse[EquityResearchReport])
async def get_research(ticker: str) -> ApiResponse[EquityResearchReport]:
    return await _run(ResearchRequest(ticker=ticker))
