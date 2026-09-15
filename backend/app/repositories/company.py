"""Company identity repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.repositories.base import Repository


class CompanyRepository(Repository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, company_id: UUID) -> Company | None:
        return await self.scalar_one_or_none(
            select(Company).where(Company.id == company_id),
            "get company",
        )

    async def get_by_ticker(self, ticker: str) -> Company | None:
        return await self.scalar_one_or_none(
            select(Company).where(Company.ticker == ticker.strip().upper()),
            "get company by ticker",
        )

    async def create(
        self,
        *,
        ticker: str,
        name: str | None = None,
        cik: str | None = None,
        exchange: str | None = None,
        currency: str | None = None,
    ) -> Company:
        company = Company(
            ticker=ticker.strip().upper(),
            name=name,
            cik=cik,
            exchange=exchange,
            currency=currency,
        )
        self.session.add(company)
        await self.flush("create company")
        return company
