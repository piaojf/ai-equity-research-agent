"""Research task lifecycle repository."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ResearchTaskStatus
from app.models.research_task import ResearchTask
from app.repositories.base import Repository


class ResearchTaskRepository(Repository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, task_id: UUID) -> ResearchTask | None:
        return await self.scalar_one_or_none(
            select(ResearchTask)
            .options(selectinload(ResearchTask.report))
            .where(ResearchTask.id == task_id),
            "get research task",
        )

    async def create(
        self,
        *,
        ticker: str,
        question: str | None = None,
        include_sec_research: bool = False,
        company_id: UUID | None = None,
        request_id: str | None = None,
    ) -> ResearchTask:
        task = ResearchTask(
            ticker=ticker.strip().upper(),
            question=question,
            include_sec_research=include_sec_research,
            company_id=company_id,
            request_id=request_id,
        )
        self.session.add(task)
        await self.flush("create research task")
        return task

    async def mark_running(self, task: ResearchTask) -> ResearchTask:
        task.status = ResearchTaskStatus.RUNNING
        task.started_at = datetime.now(UTC)
        await self.flush("mark research task running")
        return task

    async def mark_stage(self, task: ResearchTask, stage: str) -> ResearchTask:
        task.current_stage = stage
        await self.flush("mark research task stage")
        return task

    async def mark_completed(self, task: ResearchTask) -> ResearchTask:
        task.status = ResearchTaskStatus.COMPLETED
        task.completed_at = datetime.now(UTC)
        await self.flush("mark research task completed")
        return task

    async def mark_failed(
        self,
        task: ResearchTask,
        *,
        error_code: str,
        error_message: str,
    ) -> ResearchTask:
        task.status = ResearchTaskStatus.FAILED
        task.error_code = error_code
        task.error_message = error_message
        task.completed_at = datetime.now(UTC)
        await self.flush("mark research task failed")
        return task
