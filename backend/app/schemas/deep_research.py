from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class DeepResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    ticker: str = Field(min_length=1, max_length=10)
    question: str = Field(min_length=1, max_length=2_000)


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    evidence_id: str = Field(min_length=1, max_length=128)
    source: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    url: HttpUrl | None = None
    published_at: datetime | None = None
    summary: str = Field(min_length=1, max_length=4_000)
    evidence_type: Literal["market", "news", "announcement", "sec"]


class MajorEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    event_date: date | None = None
    description: str = Field(min_length=1, max_length=2_000)
    evidence_ids: list[str] = Field(min_length=1, max_length=20)


class DeepResearchReport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    ticker: str = Field(min_length=1, max_length=10)
    question: str = Field(min_length=1, max_length=2_000)
    conclusion: str = Field(min_length=1, max_length=8_000)
    major_events: list[MajorEvent] = Field(default_factory=list, max_length=50)
    evidence: list[Evidence] = Field(default_factory=list, max_length=100)
    confidence: Literal["low", "medium", "high"]
    limitations: list[str] = Field(default_factory=list, max_length=100)


class DeepResearchAccepted(BaseModel):
    task_id: UUID
    status: Literal["queued"] = "queued"


class DeepResearchTaskStatus(BaseModel):
    task_id: UUID
    status: Literal["queued", "running", "completed", "failed"]
    report: DeepResearchReport | None = None
    error: str | None = None
