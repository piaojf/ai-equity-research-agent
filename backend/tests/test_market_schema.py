from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from app.schemas.market import HistoricalPricePoint, PriceSnapshot


def test_historical_point_rejects_invalid_ohlc() -> None:
    with pytest.raises(ValidationError):
        HistoricalPricePoint(
            date=date(2026, 9, 14),
            open=180,
            high=179,
            low=181,
            close=180,
            volume=1,
        )


def test_price_snapshot_requires_positive_price() -> None:
    with pytest.raises(ValidationError):
        PriceSnapshot(
            ticker="NVDA",
            price=0,
            currency="USD",
            as_of=datetime(2026, 9, 14, tzinfo=UTC),
            retrieved_at=datetime(2026, 9, 14, 20, tzinfo=UTC),
            source="mock",
            is_delayed=True,
        )
