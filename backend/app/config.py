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
    # Main reasoning model (CV reading, scoring). Switch to the Nemotron 3.5 Super VL ID
    # once `GET /v1/models` lists it (run `uv run python scripts/list_models.py`).
    nemotron_model: str = "nvidia/nemotron-3-super-120b-a12b"
    # Cheap/fast model for high-volume sub-agent steps. Defaults to the main model because it
    # is the only ID confirmed on Token Factory; swap in Nemotron 3.5 Lightning 30B when listed.
    nemotron_fast_model: str = "nvidia/nemotron-3-super-120b-a12b"
    llm_timeout_seconds: float = 120.0
    llm_max_tokens: int = 8000  # reasoning tokens count toward this, keep it generous

    # --- Tavily ---
    tavily_api_key: str | None = None

    # --- App ---
    mock_mode: bool = False
    max_postings: int = Field(default=10, ge=1, le=20)
    cors_origins: str = "http://localhost:3000"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

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
