"""SEC filing identity repository."""

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FilingType
from app.models.filing import Filing
from app.repositories.base import Repository


class FilingRepository(Repository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, filing_id: UUID) -> Filing | None:
        return await self.scalar_one_or_none(
            select(Filing).where(Filing.id == filing_id),
            "get filing",
        )

    async def get_by_accession(self, accession_number: str) -> Filing | None:
        return await self.scalar_one_or_none(
            select(Filing).where(Filing.accession_number == accession_number),
            "get filing by accession number",
        )

    async def list_for_company(
        self,
        company_id: UUID,
        *,
        filing_type: FilingType | None = None,
    ) -> list[Filing]:
        statement = select(Filing).where(Filing.company_id == company_id)
        if filing_type is not None:
            statement = statement.where(Filing.filing_type == filing_type)
        statement = statement.order_by(Filing.filing_date.desc())
        result = await self.execute(statement, "list company filings")
        return list(result.scalars().all())

    async def create(
        self,
        *,
        company_id: UUID,
        ticker: str,
        filing_type: FilingType,
        filing_date: date,
        accession_number: str,
        source_url: str,
    ) -> Filing:
        filing = Filing(
            company_id=company_id,
            ticker=ticker.strip().upper(),
            filing_type=filing_type,
            filing_date=filing_date,
            accession_number=accession_number,
            source_url=source_url,
        )
        self.session.add(filing)
        await self.flush("create filing")
        return filing
