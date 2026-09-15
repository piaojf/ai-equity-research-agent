from typing import Literal

from pydantic import BaseModel


class HealthErrorResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    environment: str
    data_mode: Literal["mock", "real", "hybrid"]
