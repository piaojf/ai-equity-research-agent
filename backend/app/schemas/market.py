from datetime import UTC, date, datetime

from pydantic import BaseModel, Field, HttpUrl, model_validator


class PriceSnapshot(BaseModel):
    ticker: str = Field(min_length=1)
    price: float = Field(gt=0)
    previous_close: float | None = Field(default=None, gt=0)
    change: float | None = None
    change_percent: float | None = None
    open: float | None = Field(default=None, gt=0)
    high: float | None = Field(default=None, gt=0)
    low: float | None = Field(default=None, gt=0)
    volume: int | None = Field(default=None, ge=0)
    currency: str = Field(min_length=1)
    as_of: datetime
    retrieved_at: datetime
    source: str = Field(min_length=1)
    source_url: HttpUrl | None = None
    is_delayed: bool

    @model_validator(mode="after")
    def validate_range(self) -> "PriceSnapshot":
        if self.high is not None and self.low is not None and self.high < self.low:
            raise ValueError("high must be greater than or equal to low")
        return self


class HistoricalPricePoint(BaseModel):
    date: date
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_ohlc(self) -> "HistoricalPricePoint":
        if self.high < self.low:
            raise ValueError("high must be greater than or equal to low")
        if not self.low <= self.open <= self.high:
            raise ValueError("open must be between low and high")
        if not self.low <= self.close <= self.high:
            raise ValueError("close must be between low and high")
        return self


class MarketHistory(BaseModel):
    ticker: str = Field(min_length=1)
    period: str = Field(min_length=1)
    points: list[HistoricalPricePoint] = Field(min_length=1)
    source: str = Field(min_length=1)
    source_url: HttpUrl | None = None
    as_of: datetime
    retrieved_at: datetime
    is_delayed: bool


class StockOverview(BaseModel):
    ticker: str = Field(min_length=1)
    quote: PriceSnapshot
    history: MarketHistory


def date_as_utc(value: date) -> datetime:
    return datetime(value.year, value.month, value.day, tzinfo=UTC)
