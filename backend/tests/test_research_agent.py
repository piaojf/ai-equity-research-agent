from datetime import UTC, datetime

import pytest

from app.agents.research import build_research_graph
from app.core.errors import AppError, ErrorCode
from app.schemas.financial import FinancialMetrics, MetricValue
from app.schemas.research import NewsAnalysis, ReportInterpretation, SecResearchResult
from app.scoring.service import ScoringService
from app.tools.research import LLMReportInterpreter, MockReportInterpreter


def _metric(value: float, source: str = "fixture") -> MetricValue:
    return MetricValue(
        value=value,
        source=source,
        retrieved_at=datetime(2026, 9, 15, tzinfo=UTC),
    )


def _financial_metrics() -> FinancialMetrics:
    return FinancialMetrics(
        ticker="AAPL",
        currency="USD",
        revenue=_metric(120.0),
        revenue_growth=_metric(0.2),
        eps=_metric(2.5),
        eps_growth=_metric(0.25),
        gross_margin=_metric(0.4),
        operating_margin=_metric(0.2),
        net_income=_metric(15.0),
        free_cash_flow=_metric(32.0),
        fcf_growth=_metric(0.28),
        pe=_metric(24.0),
        forward_pe=_metric(20.0),
        peg=_metric(1.2),
    )


class FakeMarketService:
    async def get_stock_overview(self, ticker: str):  # noqa: ANN201
        del ticker
        return None


class FakeFinancialService:
    async def get_financials(self, ticker: str) -> FinancialMetrics:
        return _financial_metrics().model_copy(update={"ticker": ticker})


class FailingFinancialService:
    async def get_financials(self, ticker: str) -> FinancialMetrics:
        del ticker
        raise AppError(
            ErrorCode.FINANCIAL_DATA_UNAVAILABLE,
            "fixture failure",
            status_code=503,
        )


class PartialFinancialService:
    async def get_financials(self, ticker: str) -> FinancialMetrics:
        return FinancialMetrics(
            ticker=ticker,
            revenue_growth=_metric(0.2),
            limitations=["Only revenue growth is available in this fixture."],
        )


class InvalidTickerMarketService:
    async def get_stock_overview(self, ticker: str):  # noqa: ANN201
        del ticker
        raise AppError(ErrorCode.INVALID_TICKER, "invalid ticker", status_code=400)


class RecordingNewsTool:
    def __init__(self) -> None:
        self.tickers: list[str] = []

    async def analyze(self, ticker: str) -> NewsAnalysis:
        self.tickers.append(ticker)
        return NewsAnalysis(
            status="available", summary="No adverse headline in fixture."
        )


class RecordingSecTool:
    def __init__(self) -> None:
        self.tickers: list[str] = []

    async def research(self, ticker: str) -> SecResearchResult:
        self.tickers.append(ticker)
        return SecResearchResult(status="available", summary="Filing evidence fixture.")


class RepairingInterpreter:
    def __init__(self) -> None:
        self.repairs: list[bool] = []

    async def interpret(self, context, *, repair: bool = False):  # noqa: ANN001, ANN201
        self.repairs.append(repair)
        if not repair:
            return {"summary": "incomplete"}
        return ReportInterpretation(
            summary=f"Interpreted {context.ticker}.",
            thesis=["Verified metrics support the thesis."],
            risks=["The fixture has limited coverage."],
            catalysts=["Further verified data may improve confidence."],
        )


class AlwaysInvalidInterpreter:
    def __init__(self) -> None:
        self.calls = 0

    async def interpret(self, context, *, repair: bool = False):  # noqa: ANN001, ANN201
        del context, repair
        self.calls += 1
        return {"summary": "still incomplete"}


class FailingInterpreter:
    async def interpret(self, context, *, repair: bool = False):  # noqa: ANN001, ANN201
        del context, repair
        raise RuntimeError("provider secret should never reach the caller")


class MutatingInterpreter:
    async def interpret(self, context, *, repair: bool = False):  # noqa: ANN001, ANN201
        del repair
        context.scores["overall"].final_score = 1
        return ReportInterpretation(
            summary="Narrative only.",
            thesis=["The score remains deterministic."],
            risks=["The fixture has limited coverage."],
            catalysts=["Verified data can improve coverage."],
        )


class RecordingLLMProvider:
    name = "fixture-llm"

    def __init__(self) -> None:
        self.schemas: list[type[object]] = []

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: type[object],
    ) -> object:
        self.schemas.append(schema)
        assert "never calculate or change scores" in system_prompt
        assert "AAPL" in user_prompt
        return ReportInterpretation(
            summary="Provider narrative.",
            thesis=["The provider only interprets supplied evidence."],
            risks=["The fixture has limited coverage."],
            catalysts=["More evidence can improve coverage."],
        )


def _agent(  # noqa: ANN001
    *, financial=None, market=None, news=None, sec=None, interpreter=None
):
    return build_research_graph(
        market or FakeMarketService(),
        financial or FakeFinancialService(),
        ScoringService(),
        news_tool=news,
        sec_tool=sec,
        interpreter=interpreter,
    )


@pytest.mark.asyncio
async def test_graph_has_named_stategraph_nodes_and_produces_a_strict_report() -> None:
    news = RecordingNewsTool()
    agent = _agent(news=news)

    node_names = set(agent.graph.get_graph().nodes)
    assert {
        "intent_router",
        "market_data_node",
        "financial_analysis_node",
        "news_analysis_node",
        "sec_research_node",
        "risk_analysis_node",
        "final_report_node",
    } <= node_names

    report = await agent.ainvoke(" aapl ")

    assert report.ticker == "AAPL"
    assert report.overall_score == report.scores["overall"]
    assert report.overall_score.final_score > 0
    assert news.tickers == ["AAPL"]
    with pytest.raises(ValueError):
        type(report).model_validate({**report.model_dump(), "unexpected": True})


@pytest.mark.asyncio
async def test_optional_sec_node_runs_only_when_requested() -> None:
    sec = RecordingSecTool()
    agent = _agent(sec=sec)

    without_sec = await agent.ainvoke("AAPL")
    with_sec = await agent.ainvoke("AAPL", include_sec_research=True)

    assert without_sec.sec_research is None
    assert with_sec.sec_research is not None
    assert with_sec.sec_research.status == "available"
    assert sec.tickers == ["AAPL"]


@pytest.mark.asyncio
async def test_partial_financial_data_keeps_report_and_empties_scores() -> None:
    report = await _agent(financial=FailingFinancialService()).ainvoke("AAPL")

    assert report.financial_metrics is None
    assert report.overall_score.final_score == 0
    assert report.overall_score.components == []
    assert report.overall_score.confidence == "low"
    assert any("Financial data was unavailable" in item for item in report.limitations)


@pytest.mark.asyncio
async def test_partial_financial_metrics_are_preserved_and_reweighted() -> None:
    report = await _agent(financial=PartialFinancialService()).ainvoke("AAPL")

    assert report.financial_metrics is not None
    assert report.key_metrics == {"revenue_growth": 0.2}
    assert report.overall_score.components
    assert sum(item.weight for item in report.growth_score.components) == pytest.approx(
        1
    )
    assert "eps_growth" in report.growth_score.missing_metrics
    assert report.growth_score.confidence == "low"


@pytest.mark.asyncio
async def test_invalid_ticker_error_is_not_downgraded_to_partial_report() -> None:
    with pytest.raises(AppError) as raised:
        await _agent(market=InvalidTickerMarketService()).ainvoke("AAPL")

    assert raised.value.code == ErrorCode.INVALID_TICKER


@pytest.mark.asyncio
async def test_invalid_structured_output_gets_one_repair_and_fixed_scores() -> None:
    interpreter = RepairingInterpreter()
    report = await _agent(interpreter=interpreter).ainvoke("AAPL")

    expected = ScoringService().score_all(_financial_metrics())["overall"]
    assert interpreter.repairs == [False, True]
    assert report.overall_score == expected
    assert report.summary == "Interpreted AAPL."


@pytest.mark.asyncio
async def test_repair_is_bounded_and_llm_error_is_sanitized() -> None:
    interpreter = AlwaysInvalidInterpreter()

    with pytest.raises(AppError) as error:
        await _agent(interpreter=interpreter).ainvoke("AAPL")

    assert interpreter.calls == 2
    assert error.value.code == ErrorCode.LLM_ERROR
    assert error.value.message == "LLM interpretation failed after one repair attempt."
    assert "provider secret" not in str(error.value)


@pytest.mark.asyncio
async def test_llm_exception_is_sanitized_without_an_unbounded_retry() -> None:
    with pytest.raises(AppError) as error:
        await _agent(interpreter=FailingInterpreter()).ainvoke("AAPL")

    assert error.value.code == ErrorCode.LLM_ERROR
    assert error.value.message == "LLM interpretation failed."
    assert "provider secret" not in str(error.value)


@pytest.mark.asyncio
async def test_interpreter_cannot_mutate_deterministic_scores() -> None:
    report = await _agent(interpreter=MutatingInterpreter()).ainvoke("AAPL")

    expected = ScoringService().score_all(_financial_metrics())["overall"]
    assert report.overall_score == expected
    assert report.fundamental_score == report.scores["fundamental"]


@pytest.mark.asyncio
async def test_llm_adapter_passes_the_report_schema_to_provider() -> None:
    provider = RecordingLLMProvider()
    report = await _agent(interpreter=LLMReportInterpreter(provider)).ainvoke("AAPL")

    assert report.summary == "Provider narrative."
    assert provider.schemas == [ReportInterpretation]


@pytest.mark.asyncio
async def test_default_tools_are_local_noop_boundaries() -> None:
    report = await _agent(interpreter=MockReportInterpreter()).ainvoke("AAPL")

    assert report.news.status == "not_configured"
    assert report.sec_research is None
    assert report.financial_metrics is not None
