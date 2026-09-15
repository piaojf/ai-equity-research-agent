from datetime import UTC, datetime

import pytest

from app.core.errors import AppError, ErrorCode
from app.db.session import Database
from app.repositories.company import CompanyRepository
from app.repositories.research_report import ResearchReportRepository
from app.repositories.research_task import ResearchTaskRepository
from app.schemas.research import EquityResearchReport, NewsAnalysis
from app.schemas.scoring import ScoreBreakdown


def _score(name: str) -> ScoreBreakdown:
    return ScoreBreakdown(
        score_name=name,
        final_score=0,
        components=[],
        methodology_version="fixture",
        confidence="low",
    )


def _report() -> EquityResearchReport:
    scores = {
        name: _score(name)
        for name in ("fundamental", "growth", "valuation", "risk", "overall")
    }
    return EquityResearchReport(
        ticker="NVDA",
        generated_at=datetime(2026, 9, 15, tzinfo=UTC),
        summary="Fixture report.",
        fundamental_score=scores["fundamental"],
        growth_score=scores["growth"],
        valuation_score=scores["valuation"],
        risk_score=scores["risk"],
        overall_score=scores["overall"],
        thesis=["Fixture thesis."],
        risks=["Fixture risk."],
        catalysts=["Fixture catalyst."],
        scores=scores,
        news=NewsAnalysis(status="not_configured"),
        confidence="low",
    )


@pytest.mark.asyncio
async def test_repositories_persist_and_rehydrate_report() -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.create_schema()

    async with database.transaction() as session:
        company = await CompanyRepository(session).create(ticker="nvda")
        task = await ResearchTaskRepository(session).create(
            ticker="NVDA", company_id=company.id, request_id="req-1"
        )
        await ResearchReportRepository(session).create(task=task, report=_report())

    async with database.session() as session:
        stored_task = await ResearchTaskRepository(session).get(task.id)
        assert stored_task is not None
        assert stored_task.report is not None
        restored = ResearchReportRepository.to_schema(stored_task.report)

    assert restored.ticker == "NVDA"
    assert restored.overall_score.final_score == 0
    await database.dispose()


@pytest.mark.asyncio
async def test_transaction_rolls_back_unique_company_violation() -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.create_schema()
    async with database.transaction() as session:
        await CompanyRepository(session).create(ticker="AAPL")

    with pytest.raises(AppError) as raised:
        async with database.transaction() as session:
            await CompanyRepository(session).create(ticker="AAPL")

    assert raised.value.code == ErrorCode.DATABASE_ERROR
    await database.dispose()
