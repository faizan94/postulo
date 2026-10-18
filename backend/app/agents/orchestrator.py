"""Orchestrator: reads the CV into a profile, then runs search -> verify -> score.

CV text --extract_profile--> Profile
Profile + Preferences --search--> RawPosting[] --verify--> VerifiedPosting[] --score--> Posting[]

If too few postings survive verification, the orchestrator runs a top-up round with a wider
location (Berlin -> Germany -> World) for only the missing part, instead of returning a thin
list. (Completeness loop adapted from mathcrypto/ai-agent-orchestrator.)
"""

import logging
import time
from typing import Any

from app.agents import mock_data
from app.agents.prompts import PROFILE_SYSTEM_PROMPT
from app.agents.score_agent import score_postings
from app.agents.search_agent import search_postings
from app.agents.verify_agent import VerifiedPosting, verify_postings
from app.config import Settings
from app.models.schemas import (
    AgentStep,
    LocationPref,
    Preferences,
    Profile,
    RejectedPosting,
    SearchResponse,
)
from app.services.llm import LLMClient
from app.services.tavily_client import TavilyService

log = logging.getLogger(__name__)

MAX_CV_CHARS = 20_000
MIN_POSTINGS = 5  # idea.md: the briefing shows 5-10 postings
MAX_ROUNDS = 3
WIDER: dict[LocationPref, LocationPref | None] = {
    "Berlin": "Germany",
    "Germany": "World",
    "World": None,
}


class Trace:
    def __init__(self) -> None:
        self.steps: list[AgentStep] = []
        self._t = time.perf_counter()

    def add(self, agent: Any, message: str) -> None:
        now = time.perf_counter()
        self.steps.append(
            AgentStep(agent=agent, message=message, duration_ms=int((now - self._t) * 1000))
        )
        log.info("[%s] %s", agent, message)
        self._t = now


async def extract_profile(cv_text: str, settings: Settings, prompt: str = "") -> Profile:
    if settings.mock_mode:
        return mock_data.mock_profile()
    async with LLMClient(settings) as llm:
        user = f"CV:\n{cv_text[:MAX_CV_CHARS]}"
        if prompt.strip():
            user += f"\n\nCANDIDATE'S OWN WISHES:\n{prompt.strip()}"
        data = await llm.chat_json(
            [
                {"role": "system", "content": PROFILE_SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            reasoning="off",
            temperature=0.6,
        )
    if not isinstance(data, dict):
        data = {}
    return Profile.model_validate(
        {k: v for k, v in data.items() if k in Profile.model_fields and v is not None}
    )


async def run_job_search(
    profile: Profile, prefs: Preferences, settings: Settings
) -> SearchResponse:
    if settings.mock_mode:
        return mock_data.mock_search(profile, prefs, settings.max_postings)

    trace = Trace()
    roles = ", ".join(profile.target_roles or [profile.headline or "your profile"])
    trace.add("orchestrator", f"Planning search for {roles} in {prefs.location}")

    verified: list[VerifiedPosting] = []
    rejected: list[RejectedPosting] = []
    seen: set[str] = set()
    round_prefs: Preferences | None = prefs

    # Both constructors raise MissingAPIKeyError (-> HTTP 503) before any work starts.
    async with LLMClient(settings) as llm, TavilyService(settings) as tavily:
        for round_num in range(1, MAX_ROUNDS + 1):
            if round_prefs is None:
                break
            raw = await search_postings(profile, round_prefs, tavily, exclude=seen)
            seen.update(p.url for p in raw)
            trace.add(
                "search",
                f"Round {round_num} ({round_prefs.location}): Tavily found {len(raw)} "
                "new postings on ATS/career sites",
            )

            kept, dropped = await verify_postings(raw, tavily)
            verified += kept
            rejected += dropped
            trace.add("verify", f"{len(kept)} verified, {len(dropped)} ghost/dead removed")

            if len(verified) >= MIN_POSTINGS:
                break
            wider = WIDER[round_prefs.location]
            round_prefs = round_prefs.model_copy(update={"location": wider}) if wider else None
            if round_prefs:
                trace.add(
                    "orchestrator",
                    f"Only {len(verified)} verified so far, widening to {round_prefs.location}",
                )

        # Scoring is the expensive step: cap how many postings get an LLM call.
        to_score = verified[: settings.max_postings + 5]
        scored = await score_postings(to_score, profile, prefs, llm, tavily)
        trace.add("score", f"Scored {len(scored)} postings with {llm.model}")

    scored.sort(key=lambda p: p.score, reverse=True)
    top = scored[: settings.max_postings]
    trace.add("orchestrator", f"Returning top {len(top)} postings")
    return SearchResponse(profile=profile, postings=top, rejected=rejected, trace=trace.steps)
