from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Equity Research Agent"
    app_version: str = "0.1.0"
    app_env: str = "development"
    data_mode: Literal["mock", "real", "hybrid"] = Field(default="mock")
    market_provider: Literal["yahoo", "alpha_vantage"] = "yahoo"
    alpha_vantage_api_key: SecretStr | None = None
    sec_user_agent: SecretStr | None = None
    deepseek_api_key: SecretStr | None = None
    deepseek_model: str = "deepseek-flash"
    deepseek_base_url: str = "https://api.deepseek.com"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    provider_timeout_seconds: float = Field(default=10.0, gt=0)
    provider_max_retries: int = Field(default=2, ge=0, le=5)
    provider_retry_delay_seconds: float = Field(default=1.0, ge=0)
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"
    database_url: str = "postgresql+asyncpg://equity:equity@postgres:5432/equity"
    redis_url: str = "redis://redis:6379/0"
    qdrant_url: str = "http://qdrant:6333"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
