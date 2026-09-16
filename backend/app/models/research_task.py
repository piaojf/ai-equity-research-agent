"""Durable lifecycle record for synchronous and background research."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel
from app.models.enums import ResearchTaskStatus

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.research_report import ResearchReport


class ResearchTask(TimestampedModel):
    __tablename__ = "research_tasks"
    __table_args__ = (
        Index("ix_research_tasks_status_created_at", "status", "created_at"),
        Index("ix_research_tasks_company_created_at", "company_id", "created_at"),
    )

    company_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        index=True,
    )
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    question: Mapped[str | None] = mapped_column(Text)
    include_sec_research: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    current_stage: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[ResearchTaskStatus] = mapped_column(
        Enum(ResearchTaskStatus, native_enum=False, length=16),
        default=ResearchTaskStatus.QUEUED,
        nullable=False,
    )
    request_id: Mapped[str | None] = mapped_column(String(128), index=True)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company | None"] = relationship(back_populates="tasks")
    report: Mapped["ResearchReport | None"] = relationship(
        back_populates="task",
        uselist=False,
    )
