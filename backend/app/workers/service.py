from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.core.errors import AppError, ErrorCode
from app.db.session import Database
from app.deep_research.graph import DeepResearchGraph
from app.repositories.research_report import ResearchReportRepository
from app.repositories.research_task import ResearchTaskRepository
from app.schemas.deep_research import (
    DeepResearchAccepted,
    DeepResearchReport,
    DeepResearchTaskStatus,
)
from app.workers.queue import ResearchJob, TaskQueue


@dataclass
class _TaskRecord:
    status: str = "queued"
    report: DeepResearchReport | None = None
    error: str | None = None


class DeepResearchService:
    def __init__(self, queue: TaskQueue, graph: DeepResearchGraph) -> None:
        self.queue = queue
        self.graph = graph
        self._tasks: dict[UUID, _TaskRecord] = {}

    async def submit(self, ticker: str, question: str) -> DeepResearchAccepted:
        task_id = uuid4()
        self._tasks[task_id] = _TaskRecord()
        await self.queue.enqueue(ResearchJob(task_id, ticker, question))
        return DeepResearchAccepted(task_id=task_id)

    def status(self, task_id: UUID) -> DeepResearchTaskStatus | None:
        record = self._tasks.get(task_id)
        if record is None:
            return None
        return DeepResearchTaskStatus(
            task_id=task_id,
            status=record.status,  # type: ignore[arg-type]
            report=record.report,
            error=record.error,
        )

    async def run_once(self) -> bool:
        job = await self.queue.dequeue()
        if job is None:
            return False
        record = self._tasks[job.task_id]
        record.status = "running"
        try:
            record.report = await self.graph.ainvoke(job.ticker, job.question)
            record.status = "completed"
        except Exception:
            record.status = "failed"
            record.error = "Deep research worker failed."
        return True


class DurableDeepResearchService:
    """PostgreSQL source of truth with ARQ as the execution transport."""

    def __init__(
        self,
        database: Database,
        queue: TaskQueue,
    ) -> None:
        self.database = database
        self.queue = queue

    async def submit(
        self,
        ticker: str,
        question: str,
        *,
        request_id: str,
    ) -> DeepResearchAccepted:
        async with self.database.transaction() as session:
            task = await ResearchTaskRepository(session).create(
                ticker=ticker,
                question=question,
                request_id=request_id,
            )
            task_id = task.id
        try:
            await self.queue.enqueue(
                ResearchJob(
                    task_id=task_id,
                    ticker=ticker.strip().upper(),
                    question=question,
                    request_id=request_id,
                )
            )
        except Exception as exc:
            await self._mark_failed(
                task_id,
                error_code=ErrorCode.QUEUE_UNAVAILABLE.value,
                error_message="Research task could not be queued.",
            )
            raise AppError(
                ErrorCode.QUEUE_UNAVAILABLE,
                "Research queue is unavailable.",
                status_code=503,
                retryable=True,
            ) from exc
        return DeepResearchAccepted(task_id=task_id)

    async def status(self, task_id: UUID) -> DeepResearchTaskStatus | None:
        async with self.database.session() as session:
            task = await ResearchTaskRepository(session).get(task_id)
            if task is None:
                return None
            report = (
                ResearchReportRepository.to_deep_research_schema(task.report)
                if task.report is not None
                else None
            )
            return DeepResearchTaskStatus(
                task_id=task.id,
                status=task.status.value,
                report=report,
                error=task.error_message,
            )

    async def _mark_failed(
        self,
        task_id: UUID,
        *,
        error_code: str,
        error_message: str,
    ) -> None:
        async with self.database.transaction() as session:
            task = await ResearchTaskRepository(session).get(task_id)
            if task is not None:
                await ResearchTaskRepository(session).mark_failed(
                    task,
                    error_code=error_code,
                    error_message=error_message,
                )
