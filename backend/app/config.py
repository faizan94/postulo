"""Application settings, loaded from environment variables and `.env`.

Lookup order (later wins): `../.env` (repo root, shared with docker compose),
`./.env` (backend folder), then real environment variables.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Nebius Token Factory (OpenAI-compatible) ---
    nebius_api_key: str | None = None
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    # IDs confirmed on Token Factory via `uv run python scripts/list_models.py` (18 Oct 2026).
    # Main model: planning, CV profile. Fast model: requirements, related checks.
    # Vision model: OCR of scanned CVs (stretch, see OCR_ENABLED).
    nemotron_model: str = "nvidia/Nemotron-3.5-Super-VL"
    nemotron_fast_model: str = "nvidia/Nemotron-3_5-Lightning"
    nemotron_vision_model: str = "nvidia/Nemotron-3.5-Super-VL"
    llm_timeout_seconds: float = 120.0
    llm_max_tokens: int = 8000  # reasoning tokens count toward this, keep it generous

    # --- Tavily ---
    tavily_api_key: str | None = None

    # --- App ---
    mock_mode: bool = False
    max_postings: int = Field(default=10, ge=1, le=20)
    cors_origins: str = "http://localhost:3000"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # --- Storage ---
    # Relative SQLite paths resolve against the working directory (backend/ locally, /app in
    # Docker). The parent folder is created on startup.
    database_url: str = "sqlite+aiosqlite:///./data/postulo.db"

    # --- Pipeline limits and freshness ---
    ocr_enabled: bool = False
    max_tavily_credits_per_run: int = Field(default=20, ge=1)
    max_llm_calls_per_run: int = Field(default=15, ge=1)
    recent_days: int = Field(default=45, ge=1)
    posting_recheck_hours: int = Field(default=24, ge=1)
    company_cache_days: int = Field(default=30, ge=1)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def nebius_configured(self) -> bool:
        return bool(self.nebius_api_key)

    @property
    def tavily_configured(self) -> bool:
        return bool(self.tavily_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
