from typing import Protocol

from pydantic import BaseModel

from app.schemas.research import (
    NewsAnalysis,
    ReportInterpretation,
    ResearchContext,
    SecResearchResult,
)


class NewsAnalysisTool(Protocol):
    async def analyze(self, ticker: str) -> NewsAnalysis: ...


class SecResearchTool(Protocol):
    async def research(self, ticker: str) -> SecResearchResult: ...


class ReportInterpreter(Protocol):
    async def interpret(
        self,
        context: ResearchContext,
        *,
        repair: bool = False,
    ) -> object: ...


class LLMProvider(Protocol):
    name: str

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
    ) -> BaseModel: ...


class LLMReportInterpreter:
    """Adapter for the shared structured-output LLM provider contract."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def interpret(
        self,
        context: ResearchContext,
        *,
        repair: bool = False,
    ) -> object:
        repair_hint = (
            " Return only valid ReportInterpretation fields." if repair else ""
        )
        return await self.provider.generate_structured(
            system_prompt=(
                "Explain supplied evidence only; never calculate or change scores."
                + repair_hint
            ),
            user_prompt=context.model_dump_json(),
            schema=ReportInterpretation,
        )


class MockNewsAnalysisTool:
    """No-op news boundary for local development and deterministic tests."""

    async def analyze(self, ticker: str) -> NewsAnalysis:
        del ticker
        return NewsAnalysis(
            status="not_configured",
            summary="News analysis is not configured in this phase.",
            limitations=["News provider is intentionally deferred to a later phase."],
        )


class MockSecResearchTool:
    """No-op SEC research boundary until the SEC RAG phase."""

    async def research(self, ticker: str) -> SecResearchResult:
        del ticker
        return SecResearchResult(
            status="not_configured",
            limitations=["SEC RAG is intentionally deferred to a later phase."],
        )


class MockReportInterpreter:
    """Deterministic narrative tool; it does not calculate or alter scores."""

    async def interpret(
        self,
        context: ResearchContext,
        *,
        repair: bool = False,
    ) -> ReportInterpretation:
        del repair
        available = context.financial_metrics is not None
        summary = (
            f"{context.ticker} has a deterministic research score of "
            f"{context.scores['overall'].final_score}."
            if available
            else (
                f"{context.ticker} has insufficient financial data for a full analysis."
            )
        )
        return ReportInterpretation(
            summary=summary,
            fundamental_view=(
                "Fundamental metrics are evaluated by the deterministic scoring engine."
            ),
            valuation_view=(
                "Valuation multiples are evaluated only when sourced metrics are "
                "available."
            ),
            sentiment="Sentiment is unavailable until the news provider is configured.",
            thesis=["The report is based on deterministic, source-attributed metrics."],
            risks=[
                "Data completeness and provider availability can limit the analysis."
            ],
            catalysts=[
                "Additional verified market, news, and filing data can improve "
                "coverage."
            ],
        )


def empty_news_analysis() -> NewsAnalysis:
    return NewsAnalysis(
        status="not_configured",
        limitations=["News provider is intentionally deferred to a later phase."],
    )


def empty_sec_research() -> SecResearchResult:
    return SecResearchResult(
        status="not_configured",
        limitations=["SEC RAG is intentionally deferred to a later phase."],
    )
