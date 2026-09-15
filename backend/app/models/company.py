"""Company identity persisted independently from provider payloads."""

from typing import TYPE_CHECKING

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.filing import Filing
    from app.models.research_task import ResearchTask


class Company(TimestampedModel):
    __tablename__ = "companies"
    __table_args__ = (UniqueConstraint("ticker", name="uq_companies_ticker"),)

    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    cik: Mapped[str | None] = mapped_column(String(20), index=True)
    exchange: Mapped[str | None] = mapped_column(String(32))
    currency: Mapped[str | None] = mapped_column(String(8))

    tasks: Mapped[list["ResearchTask"]] = relationship(back_populates="company")
    filings: Mapped[list["Filing"]] = relationship(back_populates="company")
