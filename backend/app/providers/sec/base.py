from datetime import date
from typing import Protocol

from pydantic import BaseModel, Field, HttpUrl


class FilingMetadata(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    filing_type: str = Field(min_length=1, max_length=16)
    filing_date: date
    accession_number: str = Field(min_length=1, max_length=64)
    source_url: HttpUrl


class SECProvider(Protocol):
    name: str

    async def list_filings(
        self, ticker: str, forms: list[str]
    ) -> list[FilingMetadata]: ...

    async def fetch_filing(self, filing: FilingMetadata) -> str: ...
