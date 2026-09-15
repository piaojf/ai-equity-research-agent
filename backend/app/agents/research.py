from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, TypedDict, cast

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from app.core.errors import AppError, ErrorCode
from app.schemas.financial import FinancialMetrics
from app.schemas.market import StockOverview
from app.schemas.research import (
    EquityResearchReport,
    NewsAnalysis,
    ReportInterpretation,
    ResearchContext,
    ResearchIntent,
    ResearchRequest,
    SecResearchResult,
)
from app.schemas.scoring import ScoreBreakdown
from app.scoring.service import ScoringService
from app.services.market import normalize_ticker
from app.tools.research import (
    MockNewsAnalysisTool,
    MockReportInterpreter,
    MockSecResearchTool,
    NewsAnalysisTool,
    ReportInterpreter,
    SecResearchTool,
    empty_news_analysis,
)


class ResearchState(TypedDict, total=False):
    ticker: str
    question: str | None
    include_sec_research: bool
    intent: ResearchIntent
    market_data: StockOverview | None
    financial_metrics: FinancialMetrics | None
    news: NewsAnalysis
    sec_research: SecResearchResult | None
    scores: dict[str, ScoreBreakdown]
    limitations: list[str]
    errors: list[str]
    report: EquityResearchReport


class MarketResearchService(Protocol):
    async def get_stock_overview(self, ticker: str) -> StockOverview: ...


class FinancialResearchService(Protocol):
    async def get_financials(self, ticker: str) -> FinancialMetrics: ...


class ScoringResearchService(Protocol):
    def score_all(self, metrics: FinancialMetrics) -> dict[str, ScoreBreakdown]: ...


class CompiledResearchGraph(Protocol):
    async def ainvoke(self, input: ResearchState) -> object: ...


class _InvalidStructuredOutput(Exception):
    """Internal marker that permits exactly one structured-output repair."""


class ResearchGraph:
    """Build and execute the research graph with all I/O dependencies injected."""

    def __init__(
        self,
        market_service: MarketResearchService,
        financial_service: FinancialResearchService,
        scoring_service: ScoringResearchService,
        *,
        news_tool: NewsAnalysisTool | None = None,
        sec_tool: SecResearchTool | None = None,
        interpreter: ReportInterpreter | None = None,
    ) -> None:
        self.market_service = market_service
        self.financial_service = financial_service
        self.scoring_service = scoring_service
        self.news_tool = news_tool or MockNewsAnalysisTool()
        self.sec_tool = sec_tool or MockSecResearchTool()
        self.interpreter = interpreter or MockReportInterpreter()
        self.graph: CompiledResearchGraph = self._build_graph()

    def _build_graph(self) -> CompiledResearchGraph:
        builder = StateGraph(ResearchState)
        builder.add_node("intent_router", self.intent_router)
        builder.add_node("market_data_node", self.market_data_node)
        builder.add_node("financial_analysis_node", self.financial_analysis_node)
        builder.add_node("news_analysis_node", self.news_analysis_node)
        builder.add_node("sec_research_node", self.sec_research_node)
        builder.add_node("risk_analysis_node", self.risk_analysis_node)
        builder.add_node("final_report_node", self.final_report_node)

        builder.add_edge(START, "intent_router")
        builder.add_edge("intent_router", "market_data_node")
        builder.add_edge("market_data_node", "financial_analysis_node")
        builder.add_edge("financial_analysis_node", "news_analysis_node")
        builder.add_conditional_edges(
            "news_analysis_node",
            self._route_sec_research,
            {
                "sec_research_node": "sec_research_node",
                "risk_analysis_node": "risk_analysis_node",
            },
        )
        builder.add_edge("sec_research_node", "risk_analysis_node")
        builder.add_edge("risk_analysis_node", "final_report_node")
        builder.add_edge("final_report_node", END)
        return cast(CompiledResearchGraph, builder.compile())

    @staticmethod
    def _limitations(state: ResearchState, *items: str) -> list[str]:
        return [*state.get("limitations", []), *items]

    async def intent_router(self, state: ResearchState) -> dict[str, object]:
        request = ResearchRequest(
            ticker=state.get("ticker", ""),
            question=state.get("question"),
            include_sec_research=state.get("include_sec_research", False),
        )
        intent = ResearchIntent(
            ticker=normalize_ticker(request.ticker),
            question=request.question,
            include_sec_research=request.include_sec_research,
        )
        return {
            "ticker": intent.ticker,
            "question": intent.question,
            "include_sec_research": intent.include_sec_research,
            "intent": intent,
            "limitations": list(state.get("limitations", [])),
        }

    async def market_data_node(self, state: ResearchState) -> dict[str, object]:
        ticker = state["ticker"]
        try:
            market_data = await self.market_service.get_stock_overview(ticker)
        except AppError as exc:
            if exc.code == ErrorCode.INVALID_TICKER:
                raise
            return {
                "market_data": None,
                "limitations": self._limitations(
                    state, "Market data was unavailable for this report."
                ),
            }
        except Exception:
            return {
                "market_data": None,
                "limitations": self._limitations(
                    state, "Market data encountered an unexpected provider error."
                ),
            }
        return {"market_data": market_data}

    async def financial_analysis_node(self, state: ResearchState) -> dict[str, object]:
        ticker = state["ticker"]
        try:
            financial_metrics = await self.financial_service.get_financials(ticker)
        except AppError as exc:
            if exc.code == ErrorCode.INVALID_TICKER:
                raise
            return {
                "financial_metrics": None,
                "limitations": self._limitations(
                    state, "Financial data was unavailable for this report."
                ),
            }
        except Exception:
            return {
                "financial_metrics": None,
                "limitations": self._limitations(
                    state, "Financial data encountered an unexpected provider error."
                ),
            }
        return {"financial_metrics": financial_metrics}

    async def news_analysis_node(self, state: ResearchState) -> dict[str, object]:
        try:
            news = await self.news_tool.analyze(state["ticker"])
        except Exception:
            news = NewsAnalysis(
                status="unavailable",
                limitations=["News analysis failed and was omitted."],
            )
        limitations = self._limitations(state, *news.limitations)
        return {"news": news, "limitations": limitations}

    def _route_sec_research(self, state: ResearchState) -> str:
        if state.get("include_sec_research", False):
            return "sec_research_node"
        return "risk_analysis_node"

    async def sec_research_node(self, state: ResearchState) -> dict[str, object]:
        try:
            sec_research = await self.sec_tool.research(state["ticker"])
        except Exception:
            sec_research = SecResearchResult(
                status="unavailable",
                limitations=["SEC research failed and was omitted."],
            )
        return {
            "sec_research": sec_research,
            "limitations": self._limitations(state, *sec_research.limitations),
        }

    @staticmethod
    def _empty_scores(reason: str) -> dict[str, ScoreBreakdown]:
        names = ("fundamental", "growth", "valuation", "risk", "overall")
        return {
            name: ScoreBreakdown(
                score_name=name,
                final_score=0,
                components=[],
                methodology_version="phase3b-1.0",
                limitations=[reason],
                confidence="low",
            )
            for name in names
        }

    async def risk_analysis_node(self, state: ResearchState) -> dict[str, object]:
        metrics = state.get("financial_metrics")
        if metrics is None:
            reason = "Financial data was unavailable; deterministic scores are empty."
            return {
                "scores": self._empty_scores(reason),
                "limitations": self._limitations(state, reason),
            }
        try:
            scores = self.scoring_service.score_all(metrics)
        except Exception:
            reason = "Deterministic scoring failed; scores are empty."
            return {
                "scores": self._empty_scores(reason),
                "limitations": self._limitations(state, reason),
            }
        return {"scores": scores}

    async def _interpret(
        self,
        context: ResearchContext,
        *,
        repair: bool,
    ) -> ReportInterpretation:
        try:
            raw = await self.interpreter.interpret(context, repair=repair)
        except Exception as exc:
            raise AppError(
                ErrorCode.LLM_ERROR,
                "LLM interpretation failed.",
                status_code=502,
                retryable=True,
            ) from exc
        try:
            return ReportInterpretation.model_validate(raw)
        except ValidationError as exc:
            raise _InvalidStructuredOutput from exc

    async def final_report_node(self, state: ResearchState) -> dict[str, object]:
        scores = state.get("scores") or self._empty_scores(
            "No deterministic scores were produced."
        )
        news = state.get("news") or empty_news_analysis()
        score_snapshot = {
            name: value.model_copy(deep=True) for name, value in scores.items()
        }
        context = ResearchContext(
            ticker=state["ticker"],
            market_data=state.get("market_data"),
            financial_metrics=state.get("financial_metrics"),
            scores=score_snapshot,
            news=news,
            sec_research=state.get("sec_research"),
            limitations=state.get("limitations", []),
        )
        try:
            try:
                interpretation = await self._interpret(context, repair=False)
            except _InvalidStructuredOutput:
                interpretation = await self._interpret(context, repair=True)
        except _InvalidStructuredOutput as exc:
            raise AppError(
                ErrorCode.LLM_ERROR,
                "LLM interpretation failed after one repair attempt.",
                status_code=502,
                retryable=False,
            ) from exc

        report = EquityResearchReport(
            ticker=context.ticker,
            generated_at=datetime.now(UTC),
            summary=interpretation.summary,
            fundamental_score=scores["fundamental"],
            growth_score=scores["growth"],
            valuation_score=scores["valuation"],
            risk_score=scores["risk"],
            sentiment_score=None,
            fundamental_view=interpretation.fundamental_view,
            valuation_view=interpretation.valuation_view,
            sentiment=interpretation.sentiment,
            thesis=interpretation.thesis,
            risks=interpretation.risks,
            catalysts=interpretation.catalysts,
            scores=dict(scores),
            overall_score=scores["overall"],
            market_data=context.market_data,
            financial_metrics=context.financial_metrics,
            news=context.news,
            sec_research=context.sec_research,
            key_metrics=self._key_metrics(context.financial_metrics),
            data_sources=self._data_sources(context),
            confidence=scores["overall"].confidence,
            errors=state.get("errors", []),
            limitations=[*context.limitations, *context.news.limitations],
        )
        return {"report": report}

    @staticmethod
    def _key_metrics(metrics: FinancialMetrics | None) -> dict[str, float | None]:
        if metrics is None:
            return {}
        names = (
            "revenue",
            "revenue_growth",
            "eps",
            "eps_growth",
            "gross_margin",
            "operating_margin",
            "net_income",
            "free_cash_flow",
            "fcf_growth",
            "pe",
            "forward_pe",
            "peg",
        )
        return {
            name: getattr(metrics, name).value
            for name in names
            if getattr(metrics, name) is not None
        }

    @staticmethod
    def _data_sources(context: ResearchContext) -> list[str]:
        sources: list[str] = []
        if context.market_data is not None:
            sources.extend(
                [context.market_data.quote.source, context.market_data.history.source]
            )
        if context.financial_metrics is not None:
            for name in (
                "revenue",
                "revenue_growth",
                "eps",
                "eps_growth",
                "gross_margin",
                "operating_margin",
                "net_income",
                "free_cash_flow",
                "fcf_growth",
                "pe",
                "forward_pe",
                "peg",
            ):
                metric = getattr(context.financial_metrics, name)
                if metric is not None:
                    sources.append(metric.source)
        sources.extend(article.source for article in context.news.articles)
        return list(dict.fromkeys(sources))

    async def ainvoke(
        self,
        ticker: str,
        *,
        question: str | None = None,
        include_sec_research: bool = False,
    ) -> EquityResearchReport:
        result = await self.graph.ainvoke(
            {
                "ticker": ticker,
                "question": question,
                "include_sec_research": include_sec_research,
            }
        )
        state = cast(ResearchState, result)
        return state["report"]


def build_research_graph(
    market_service: MarketResearchService,
    financial_service: FinancialResearchService,
    scoring_service: ScoringResearchService | None = None,
    *,
    news_tool: NewsAnalysisTool | None = None,
    sec_tool: SecResearchTool | None = None,
    interpreter: ReportInterpreter | None = None,
) -> ResearchGraph:
    """Create a compiled StateGraph with no hidden network clients."""

    return ResearchGraph(
        market_service,
        financial_service,
        scoring_service or ScoringService(),
        news_tool=news_tool,
        sec_tool=sec_tool,
        interpreter=interpreter,
    )
