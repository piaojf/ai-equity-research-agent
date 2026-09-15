from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Equity Research Agent"
    app_version: str = "0.1.0"
    app_env: str = "development"
    data_mode: Literal["mock", "real", "hybrid"] = Field(default="mock")
    market_provider: Literal["alpha_vantage"] = "alpha_vantage"
    alpha_vantage_api_key: SecretStr | None = None
    provider_timeout_seconds: float = Field(default=10.0, gt=0)
    provider_max_retries: int = Field(default=2, ge=0, le=5)
    provider_retry_delay_seconds: float = Field(default=1.0, ge=0)
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
