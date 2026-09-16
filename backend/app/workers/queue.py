from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from arq.connections import ArqRedis


@dataclass(frozen=True, slots=True)
class ResearchJob:
    task_id: UUID
    ticker: str
    question: str
    request_id: str = ""


class TaskQueue(Protocol):
    async def enqueue(self, job: ResearchJob) -> None: ...
    async def dequeue(self) -> ResearchJob | None: ...


class InMemoryTaskQueue:
    def __init__(self) -> None:
        self.jobs: list[ResearchJob] = []

    async def enqueue(self, job: ResearchJob) -> None:
        self.jobs.append(job)

    async def dequeue(self) -> ResearchJob | None:
        return self.jobs.pop(0) if self.jobs else None


class RedisTaskQueue:
    """ARQ producer boundary used by the real application runtime."""

    def __init__(self, pool: ArqRedis) -> None:
        self.pool = pool

    async def enqueue(self, job: ResearchJob) -> None:
        await self.pool.enqueue_job(
            "run_deep_research",
            str(job.task_id),
            job.ticker,
            job.question,
            request_id=job.request_id,
            _job_id=f"deep-research:{job.task_id}",
        )

    async def dequeue(self) -> ResearchJob | None:
        # ARQ workers consume Redis jobs; HTTP processes never dequeue directly.
        return None
