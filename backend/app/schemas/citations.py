from datetime import date

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    ticker: str = Field(min_length=1, max_length=10)
    filing_type: str = Field(min_length=1, max_length=16)
    filing_date: date
    accession_number: str = Field(min_length=1, max_length=64)
    section: str = Field(min_length=1, max_length=200)
    chunk_id: str = Field(min_length=1, max_length=200)
    source_url: HttpUrl
    excerpt: str = Field(min_length=1, max_length=10_000)
    page_or_anchor: str | None = Field(default=None, max_length=200)
