from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResearchJob:
    task_id: UUID
    ticker: str
    question: str


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
