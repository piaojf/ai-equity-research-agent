"""Immutable-ish serialized report snapshot linked to its task."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.research_task import ResearchTask


REPORT_PAYLOAD = JSON().with_variant(JSONB, "postgresql")


class ResearchReport(TimestampedModel):
    __tablename__ = "research_reports"
    __table_args__ = (
        UniqueConstraint("task_id", name="uq_research_reports_task_id"),
        Index("ix_research_reports_company_generated_at", "company_id", "generated_at"),
        Index("ix_research_reports_ticker_generated_at", "ticker", "generated_at"),
    )

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        index=True,
    )
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(REPORT_PAYLOAD, nullable=False)

    task: Mapped["ResearchTask"] = relationship(back_populates="report")
    company: Mapped["Company | None"] = relationship()
