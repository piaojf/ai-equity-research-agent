"""SEC filing identity used by the later RAG ingestion phase."""

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel
from app.models.enums import FilingType

if TYPE_CHECKING:
    from app.models.company import Company


class Filing(TimestampedModel):
    __tablename__ = "filings"
    __table_args__ = (
        UniqueConstraint("accession_number", name="uq_filings_accession_number"),
        Index("ix_filings_company_filing_date", "company_id", "filing_date"),
        Index("ix_filings_ticker_filing_date", "ticker", "filing_date"),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    filing_type: Mapped[FilingType] = mapped_column(
        String(16),
        nullable=False,
    )
    filing_date: Mapped[date] = mapped_column(Date, nullable=False)
    accession_number: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)

    company: Mapped["Company"] = relationship(back_populates="filings")
