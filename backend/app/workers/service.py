from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.deep_research.graph import DeepResearchGraph
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
