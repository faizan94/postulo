"""One gate for all LLM calls in a run: budget, availability and graceful fallback."""

import logging
from typing import Any

from app.config import Settings
from app.errors import PostuloError
from app.services.llm import LLMClient

log = logging.getLogger(__name__)


class LLMGate:
    """Counts calls against MAX_LLM_CALLS_PER_RUN and stops trying after the first outage.

    `call_json` returns None instead of raising, so every caller has a rule-based fallback.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = not settings.mock_mode and bool(settings.nebius_api_key)
        self.calls = 0
        self.down_reason: str | None = None if self.enabled else "AI disabled"

    @property
    def usable(self) -> bool:
        return (
            self.enabled
            and self.down_reason is None
            and self.calls < self.settings.max_llm_calls_per_run
        )

    async def call_json(
        self, messages: list[dict[str, Any]], *, fast: bool = False, reasoning: str = "off"
    ) -> Any | None:
        if not self.usable:
            return None
        self.calls += 1
        try:
            async with LLMClient(self.settings) as llm:
                return await llm.chat_json(messages, fast=fast, reasoning=reasoning)
        except PostuloError as e:
            log.warning("LLM unavailable, falling back to rules: %s", e.message)
            self.down_reason = e.message
            return None

    @property
    def model_label(self) -> str:
        return self.settings.nemotron_fast_model
