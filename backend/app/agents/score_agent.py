"""Score agent: reads each posting and tags every required skill gold/orange/red."""

import asyncio
import json
import logging
from typing import Any

from app.agents.prompts import SCORE_SYSTEM_PROMPT
from app.agents.verify_agent import VerifiedPosting
from app.models.schemas import Posting, Preferences, Profile, Skill
from app.services.llm import LLMClient
from app.services.tavily_client import TavilyService

log = logging.getLogger(__name__)

MAX_POSTING_CHARS = 12_000


def fallback_score(skills: list[Skill]) -> float:
    if not skills:
        return 0.0
    points = sum({"gold": 1.0, "orange": 0.5, "red": 0.0}[s.status] for s in skills)
    return round(points / len(skills) * 10) / 2  # 0-5 in 0.5 steps


def to_posting(vp: VerifiedPosting, data: dict[str, Any]) -> Posting:
    skills = [
        Skill(name=str(s["name"]), status=s["status"], note=s.get("note"))
        for s in data.get("skills", [])
        if isinstance(s, dict) and s.get("name") and s.get("status") in ("gold", "orange", "red")
    ]
    try:
        score = float(data["score"])
    except (KeyError, TypeError, ValueError):
        score = fallback_score(skills)
    score = max(0.0, min(5.0, round(score * 2) / 2))
    raw = vp.raw
    return Posting(
        title=data.get("title") or raw.title,
        company=data.get("company") or raw.company or "Unknown company",
        url=raw.url,
        posted=data.get("posted") or raw.published_date,
        location=data.get("location"),
        source=raw.source,
        verified=vp.flags,
        score=score,
        skills=skills,
        why=data.get("why") or "",
    )


async def score_postings(
    postings: list[VerifiedPosting],
    profile: Profile,
    prefs: Preferences,
    llm: LLMClient,
    tavily: TavilyService,
) -> list[Posting]:
    pages = await tavily.extract([p.raw.url for p in postings]) if postings else {}
    profile_json = profile.model_dump_json(exclude_none=True)
    sem = asyncio.Semaphore(4)
    errors: list[Exception] = []

    async def score_one(vp: VerifiedPosting) -> Posting | None:
        text = pages.get(vp.raw.url) or vp.raw.snippet
        user = (
            f"CANDIDATE PROFILE:\n{profile_json}\n\n"
            f"CANDIDATE WISHES: location={prefs.location}; {prefs.prompt or '(none)'}\n\n"
            f"POSTING ({vp.raw.url}):\nTitle: {vp.raw.title}\n{text[:MAX_POSTING_CHARS]}"
        )
        async with sem:
            try:
                data = await llm.chat_json(
                    [
                        {"role": "system", "content": SCORE_SYSTEM_PROMPT},
                        {"role": "user", "content": user},
                    ],
                    reasoning="on",
                )
            except Exception as e:  # one bad posting must not kill the run
                log.warning("Scoring failed for %s: %s", vp.raw.url, e)
                errors.append(e)
                return None
        if not isinstance(data, dict):
            log.warning(
                "Scoring returned non-object for %s: %s", vp.raw.url, json.dumps(data)[:200]
            )
            return None
        return to_posting(vp, data)

    results = await asyncio.gather(*(score_one(p) for p in postings))
    scored = [p for p in results if p is not None]
    if postings and not scored and errors:
        raise errors[0]  # every call failed: surface it (bad key, wrong model ID, ...)
    return scored
