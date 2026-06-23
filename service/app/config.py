"""Application configuration (single source).

Settings are read from the environment. There is exactly one settings object;
the legacy repo's scattered config layers are not ported.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EVENTRELAY_", extra="ignore")

    app_name: str = "EventRelay API"
    app_version: str = "0.1.0"
    environment: str = "development"

    # SC6 persistence. When unset, the in-memory store is used (tests/local).
    # In production (Cloud Run) this is a Postgres async DSN, e.g.
    #   postgresql+asyncpg://user:pass@host:5432/eventrelay
    database_url: str | None = None

    # Pipeline version — part of the idempotency key (SC6). Bump when the
    # pipeline's output for a given URL would legitimately change.
    pipeline_version: str = "1"

    # Model seam (SC3/SC4). Default provider is Gemini; swap in the container
    # for Anthropic/OpenAI by implementing the same LLMClient interface.
    gemini_api_key: str | None = None
    llm_model: str = "gemini-2.5-flash"


@lru_cache
def get_settings() -> Settings:
    return Settings()
