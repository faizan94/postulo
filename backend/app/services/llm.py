"""Thin wrapper around the OpenAI SDK pointed at Nebius Token Factory (Nemotron).

Usage:
    async with LLMClient(settings) as llm:
        text = await llm.chat([{"role": "user", "content": "hi"}], reasoning="off")
        data = await llm.chat_json(messages, reasoning="on")
"""

import json
import logging
import re
from typing import Any, Literal, Self

import openai
from openai import AsyncOpenAI

from app.config import Settings
from app.errors import MissingAPIKeyError, UpstreamError

log = logging.getLogger(__name__)

Reasoning = Literal["off", "on", "medium"]

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def reasoning_extra_body(reasoning: Reasoning) -> dict[str, Any]:
    """Nemotron 3.x / 3.5 reasoning toggle, passed through `chat_template_kwargs`."""
    kwargs: dict[str, Any] = {"enable_thinking": reasoning != "off"}
    if reasoning == "medium":
        kwargs["medium_effort"] = True
    return {"chat_template_kwargs": kwargs}


def extract_json(text: str) -> Any:
    """Parse JSON from a model reply, tolerating <think> blocks, code fences and chatter."""
    cleaned = _THINK_RE.sub("", text).strip()
    cleaned = _FENCE_RE.sub("", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Fall back to the first balanced {...} or [...] block.
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = cleaned.find(open_ch)
        while start != -1:
            depth = 0
            in_str = False
            escape = False
            for i in range(start, len(cleaned)):
                ch = cleaned[i]
                if in_str:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == '"':
                        in_str = False
                elif ch == '"':
                    in_str = True
                elif ch == open_ch:
                    depth += 1
                elif ch == close_ch:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(cleaned[start : i + 1])
                        except json.JSONDecodeError:
                            break
            start = cleaned.find(open_ch, start + 1)
    raise ValueError("No JSON object found in model output")


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.nebius_api_key:
            raise MissingAPIKeyError("NEBIUS_API_KEY")
        self.settings = settings
        self.model = settings.nemotron_model
        self.fast_model = settings.nemotron_fast_model or settings.nemotron_model
        self._client = AsyncOpenAI(
            api_key=settings.nebius_api_key,
            base_url=settings.nebius_base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=2,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.close()

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        fast: bool = False,
        reasoning: Reasoning = "off",
        temperature: float = 1.0,
        top_p: float = 0.95,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        """Return the assistant text. `fast=True` uses NEMOTRON_FAST_MODEL."""
        chosen = model or (self.fast_model if fast else self.model)
        try:
            resp = await self._client.chat.completions.create(
                model=chosen,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens or self.settings.llm_max_tokens,
                extra_body=reasoning_extra_body(reasoning),
                **kwargs,
            )
        except openai.AuthenticationError as e:
            raise UpstreamError("Nebius rejected NEBIUS_API_KEY (401). Check the key.") from e
        except openai.NotFoundError as e:
            raise UpstreamError(
                f"Model '{chosen}' not found on Token Factory. "
                "Check NEMOTRON_MODEL against /v1/models."
            ) from e
        except openai.RateLimitError as e:
            raise UpstreamError("Nebius rate limit hit. Retry in a moment.") from e
        except openai.APITimeoutError as e:
            raise UpstreamError("Nebius request timed out.") from e
        except openai.APIStatusError as e:
            if e.status_code == 402:
                raise UpstreamError(
                    "Nebius account has no budget left (402). Add Token Factory credits."
                ) from e
            raise UpstreamError(f"Nebius API error: {e}") from e
        except openai.APIError as e:
            raise UpstreamError(f"Nebius API error: {e}") from e

        if not resp.choices:
            raise UpstreamError("Nebius returned no choices.")
        content = resp.choices[0].message.content or ""
        return _THINK_RE.sub("", content).strip()

    async def chat_json(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        """Like `chat`, but parses the reply as JSON (one retry on bad output)."""
        text = await self.chat(messages, **kwargs)
        try:
            return extract_json(text)
        except ValueError:
            log.warning("Model returned non-JSON, retrying once. First 200 chars: %r", text[:200])
        retry = [
            *messages,
            {"role": "assistant", "content": text},
            {"role": "user", "content": "Reply again with ONLY the valid JSON object, no prose."},
        ]
        text = await self.chat(retry, **{**kwargs, "reasoning": "off"})
        try:
            return extract_json(text)
        except ValueError as e:
            raise UpstreamError("Model did not return valid JSON.") from e
