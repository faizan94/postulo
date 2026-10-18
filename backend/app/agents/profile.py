"""CV text -> profile. LLM first (grounded and verified), rule-based fallback (D4)."""

import logging
from typing import Any

from pydantic import ValidationError

from app.agents.prompts.profile import PROFILE_SYSTEM_PROMPT
from app.config import Settings
from app.domain.evidence import EvidenceChecker
from app.domain.glossary import glossary
from app.domain.places import places
from app.domain.rules import extract_profile as rule_profile
from app.domain.years import seniority, years_from_roles
from app.errors import PostuloError
from app.schemas.common import Evidence
from app.schemas.profile import EducationItem, LanguageItem, Profile, Role, SkillItem
from app.services.llm import LLMClient

log = logging.getLogger(__name__)

AI_UNAVAILABLE = "AI reading is unavailable right now, so we used rule-based reading."


def llm_available(settings: Settings) -> bool:
    return not settings.mock_mode and bool(settings.nebius_api_key)


def _items(raw: Any, model: type, checker: EvidenceChecker, build: Any) -> list[Any]:
    out = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict) or not checker.check(item.get("quote")):
            continue
        try:
            out.append(build(item))
        except (ValidationError, KeyError, TypeError, ValueError):
            continue
    return out


def profile_from_llm(data: dict[str, Any], text: str) -> Profile:
    """Validate an LLM profile: keep only items whose quotes are in the CV, recompute numbers."""
    checker = EvidenceChecker(text)
    g = glossary()

    def ev(item: dict[str, Any]) -> Evidence:
        return Evidence(quote=str(item["quote"])[:500])

    skills = _items(
        data.get("skills"),
        SkillItem,
        checker,
        lambda i: SkillItem(
            name=g.canonical(str(i["name"])),
            type=i.get("type") if i.get("type") in ("tech", "domain", "soft") else "tech",
            evidence=ev(i),
        ),
    )
    roles = _items(
        data.get("roles"),
        Role,
        checker,
        lambda i: Role(
            title=str(i["title"])[:120],
            company=str(i.get("company") or "")[:120],
            start=i.get("start"),
            end=i.get("end"),
            evidence=ev(i),
        ),
    )
    languages = _items(
        data.get("languages"),
        LanguageItem,
        checker,
        lambda i: LanguageItem(
            name=g.canonical(str(i["name"])),
            level=i.get("level"),
            evidence=ev(i),
        ),
    )
    education = _items(
        data.get("education"),
        EducationItem,
        checker,
        lambda i: EducationItem(
            school=str(i["school"])[:120],
            degree=i.get("degree"),
            evidence=ev(i),
        ),
    )
    place = None
    if isinstance(data.get("place"), str) and data["place"].strip():
        hits = places().search(data["place"].split(",")[0])
        place = next((p for p in hits if p.kind == "city"), None)
    years = years_from_roles(roles)
    titles = [str(t)[:80] for t in data.get("target_titles") or [] if str(t).strip()][:3]
    return Profile(
        headline=(data.get("headline") or None),
        summary=(data.get("summary") or None),
        skills=skills,
        roles=roles,
        languages=languages,
        education=education,
        place=place,
        years_total=years,
        seniority=seniority(years),
        target_titles=titles,
    )


def merge(primary: Profile, backup: Profile) -> Profile:
    """Add rule-found items the LLM missed, so glossary skills are never lost.

    Items are de-duplicated by key, so 'React' and 'REACT' never appear twice.
    """
    g = glossary()

    def uniq(items: list[Any]) -> list[Any]:
        seen: set[str] = set()
        out = []
        for item in items:
            k = g.key_of(item.name)
            if k not in seen:
                seen.add(k)
                out.append(item)
        return out

    return primary.model_copy(
        update={
            "skills": uniq(primary.skills + backup.skills),
            "languages": uniq(primary.languages + backup.languages),
            "place": primary.place or backup.place,
            "target_titles": primary.target_titles or backup.target_titles,
            "headline": primary.headline or backup.headline,
            "roles": primary.roles or backup.roles,
            "years_total": primary.years_total if primary.roles else backup.years_total,
            "seniority": primary.seniority if primary.roles else backup.seniority,
        }
    )


async def build_profile(text: str, settings: Settings) -> tuple[Profile, list[str]]:
    backup = rule_profile(text)
    if not llm_available(settings):
        return backup, ([] if settings.mock_mode else [AI_UNAVAILABLE])
    try:
        async with LLMClient(settings) as llm:
            data = await llm.chat_json(
                [
                    {"role": "system", "content": PROFILE_SYSTEM_PROMPT},
                    {"role": "user", "content": f"<cv>\n{text}\n</cv>"},
                ],
                reasoning="off",
                temperature=0.6,
            )
    except PostuloError as e:
        log.warning("Profile LLM failed, using rules: %s", e.message)
        return backup, [AI_UNAVAILABLE]
    if not isinstance(data, dict):
        return backup, [AI_UNAVAILABLE]
    return merge(profile_from_llm(data, text), backup), []
