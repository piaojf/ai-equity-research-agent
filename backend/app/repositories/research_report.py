"""Research report snapshot repository."""

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.serialization import (
    deserialize_research_report,
    serialize_research_report,
)
from app.models.research_report import ResearchReport
from app.models.research_task import ResearchTask
from app.repositories.base import Repository
from app.schemas.deep_research import DeepResearchReport
from app.schemas.research import EquityResearchReport


class ResearchReportRepository(Repository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, report_id: UUID) -> ResearchReport | None:
        return await self.scalar_one_or_none(
            select(ResearchReport).where(ResearchReport.id == report_id),
            "get research report",
        )

    async def get_by_task_id(self, task_id: UUID) -> ResearchReport | None:
        return await self.scalar_one_or_none(
            select(ResearchReport).where(ResearchReport.task_id == task_id),
            "get research report by task",
        )

    async def create(
        self,
        *,
        task: ResearchTask,
        report: EquityResearchReport,
    ) -> ResearchReport:
        stored = ResearchReport(
            task_id=task.id,
            company_id=task.company_id,
            ticker=report.ticker,
            generated_at=report.generated_at,
            summary=report.summary,
            confidence=report.confidence,
            payload=serialize_research_report(report),
        )
        self.session.add(stored)
        await self.flush("create research report")
        return stored

    @staticmethod
    def to_schema(stored: ResearchReport) -> EquityResearchReport:
        return deserialize_research_report(stored.payload)

    async def create_deep_research(
        self,
        *,
        task: ResearchTask,
        report: DeepResearchReport,
    ) -> ResearchReport:
        stored = ResearchReport(
            task_id=task.id,
            company_id=task.company_id,
            ticker=report.ticker,
            generated_at=datetime.now(UTC),
            summary=report.conclusion,
            confidence=report.confidence,
            payload=report.model_dump(mode="json"),
        )
        self.session.add(stored)
        await self.flush("create deep research report")
        return stored

    @staticmethod
    def to_deep_research_schema(stored: ResearchReport) -> DeepResearchReport:
        return DeepResearchReport.model_validate_json(json.dumps(stored.payload))
