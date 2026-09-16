from __future__ import annotations

from datetime import date
from typing import Literal, Protocol, TypedDict, cast

from langgraph.graph import END, START, StateGraph

from app.core.errors import AppError, ErrorCode
from app.deep_research.llm import DeepResearchAnswerer
from app.schemas.deep_research import (
    DeepResearchReport,
    Evidence,
    MajorEvent,
)
from app.schemas.market import StockOverview


class DeepResearchMarketService(Protocol):
    async def get_stock_overview(self, ticker: str) -> StockOverview: ...


class EvidenceSearchTool(Protocol):
    async def search(self, ticker: str, around: list[date]) -> list[Evidence]: ...


class CompiledDeepResearchGraph(Protocol):
    async def ainvoke(self, input: DeepResearchState) -> object: ...


class DeepResearchState(TypedDict, total=False):
    ticker: str
    question: str
    market_data: StockOverview | None
    significant_dates: list[date]
    evidence: list[Evidence]
    major_events: list[MajorEvent]
    limitations: list[str]
    report: DeepResearchReport


class EmptyEvidenceSearchTool:
    def __init__(self, evidence_type: str) -> None:
        self.evidence_type = evidence_type

    async def search(self, ticker: str, around: list[date]) -> list[Evidence]:
        del ticker, around
        return []


class DeepResearchGraph:
    """Evidence-first LangGraph workflow for explaining significant moves."""

    def __init__(
        self,
        market_service: DeepResearchMarketService,
        *,
        news_tool: EvidenceSearchTool | None = None,
        announcement_tool: EvidenceSearchTool | None = None,
        sec_tool: EvidenceSearchTool | None = None,
        answerer: DeepResearchAnswerer | None = None,
    ) -> None:
        self.market_service = market_service
        self.news_tool = news_tool or EmptyEvidenceSearchTool("news")
        self.announcement_tool = announcement_tool or EmptyEvidenceSearchTool(
            "announcement"
        )
        self.sec_tool = sec_tool or EmptyEvidenceSearchTool("sec")
        self.answerer = answerer
        self.graph = self._build()

    def _build(self) -> CompiledDeepResearchGraph:
        builder = StateGraph(DeepResearchState)
        builder.add_node("understand_question", self.understand_question)
        builder.add_node("fetch_historical_price", self.fetch_historical_price)
        builder.add_node(
            "detect_significant_price_moves", self.detect_significant_price_moves
        )
        builder.add_node("search_news_around_dates", self.search_news_around_dates)
        builder.add_node(
            "search_company_announcements", self.search_company_announcements
        )
        builder.add_node("search_sec_if_necessary", self.search_sec_if_necessary)
        builder.add_node("analyze_possible_causes", self.analyze_possible_causes)
        builder.add_node("cross_check_evidence", self.cross_check_evidence)
        builder.add_node("generate_research_report", self.generate_research_report)
        builder.add_edge(START, "understand_question")
        builder.add_edge("understand_question", "fetch_historical_price")
        builder.add_edge("fetch_historical_price", "detect_significant_price_moves")
        builder.add_edge("detect_significant_price_moves", "search_news_around_dates")
        builder.add_edge("search_news_around_dates", "search_company_announcements")
        builder.add_edge("search_company_announcements", "search_sec_if_necessary")
        builder.add_edge("search_sec_if_necessary", "analyze_possible_causes")
        builder.add_edge("analyze_possible_causes", "cross_check_evidence")
        builder.add_edge("cross_check_evidence", "generate_research_report")
        builder.add_edge("generate_research_report", END)
        return cast(CompiledDeepResearchGraph, builder.compile())

    async def understand_question(self, state: DeepResearchState) -> dict[str, object]:
        ticker = state.get("ticker", "").strip().upper()
        if not ticker:
            raise AppError(
                ErrorCode.INVALID_TICKER, "Ticker is required.", status_code=400
            )
        return {"ticker": ticker, "limitations": []}

    async def fetch_historical_price(
        self, state: DeepResearchState
    ) -> dict[str, object]:
        try:
            return {
                "market_data": await self.market_service.get_stock_overview(
                    state["ticker"]
                )
            }
        except AppError as exc:
            if exc.code == ErrorCode.INVALID_TICKER:
                raise
            return {
                "market_data": None,
                "limitations": ["Historical market data was unavailable."],
            }

    async def detect_significant_price_moves(
        self, state: DeepResearchState
    ) -> dict[str, object]:
        market_data = state.get("market_data")
        if market_data is None:
            return {"significant_dates": []}
        points = market_data.history.points
        significant: list[date] = []
        for previous, current in zip(points, points[1:], strict=False):
            if previous.close and abs(current.close / previous.close - 1) >= 0.05:
                significant.append(current.date)
        return {"significant_dates": significant}

    async def search_news_around_dates(
        self, state: DeepResearchState
    ) -> dict[str, object]:
        evidence = await self.news_tool.search(
            state["ticker"], state.get("significant_dates", [])
        )
        return {"evidence": evidence}

    async def search_company_announcements(
        self, state: DeepResearchState
    ) -> dict[str, object]:
        evidence = await self.announcement_tool.search(
            state["ticker"], state.get("significant_dates", [])
        )
        return {"evidence": [*state.get("evidence", []), *evidence]}

    async def search_sec_if_necessary(
        self, state: DeepResearchState
    ) -> dict[str, object]:
        if not state.get("evidence"):
            return {"evidence": await self.sec_tool.search(state["ticker"], [])}
        return {}

    async def analyze_possible_causes(
        self, state: DeepResearchState
    ) -> dict[str, object]:
        events = [
            MajorEvent(
                event_date=e.published_at.date() if e.published_at else None,
                description=e.summary,
                evidence_ids=[e.evidence_id],
            )
            for e in state.get("evidence", [])
        ]
        return {"major_events": events}

    async def cross_check_evidence(self, state: DeepResearchState) -> dict[str, object]:
        unique: dict[str, Evidence] = {
            item.evidence_id: item for item in state.get("evidence", [])
        }
        return {"evidence": list(unique.values())}

    async def generate_research_report(
        self, state: DeepResearchState
    ) -> dict[str, object]:
        evidence = state.get("evidence", [])
        limitations = state.get("limitations", [])
        if not evidence:
            limitations = [
                *limitations,
                "No corroborating evidence was retrieved for the observed move.",
            ]
        conclusion = (
            "No sufficient evidence was retrieved to explain the move."
            if not evidence
            else "Possible causes are listed only when linked to retrieved evidence."
        )
        if self.answerer is not None and evidence:
            conclusion = await self.answerer.answer(
                state["question"], evidence, state.get("major_events", [])
            )
        confidence: Literal["low", "medium"] = (
            "low" if len(evidence) < 2 else "medium"
        )
        return {
            "report": DeepResearchReport(
                ticker=state["ticker"],
                question=state["question"],
                conclusion=conclusion,
                major_events=state.get("major_events", []),
                evidence=evidence,
                confidence=confidence,
                limitations=limitations,
            )
        }

    async def ainvoke(self, ticker: str, question: str) -> DeepResearchReport:
        result = await self.graph.ainvoke({"ticker": ticker, "question": question})
        return cast(DeepResearchState, result)["report"]
