from datetime import UTC, datetime
from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


def utc_now() -> datetime:
    return datetime.now(UTC)


class ApiResponse[T](BaseModel):
    request_id: str = Field(min_length=1)
    data: T
    errors: list[dict[str, object]] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)
