"""Open search (D21): free text -> titles, places, keywords.

Nemotron proposes, code validates (places and keywords must be written in the text), and
glossary/places rules are the fallback, so the parser always returns something usable.
"""

import re

from app.agents.llm_gate import LLMGate
from app.agents.prompts.intent import INTENT_SYSTEM_PROMPT
from app.config import Settings
from app.domain.evidence import normalize
from app.domain.glossary import glossary
from app.domain.places import places
from app.schemas.common import Place
from app.schemas.search import SearchIntent

ROLE_NOUNS = {
    "engineer",
    "developer",
    "scientist",
    "analyst",
    "manager",
    "designer",
    "architect",
    "lead",
    "consultant",
    "specialist",
    "researcher",
    "administrator",
    "owner",
    "director",
    "entwickler",
    "ingenieur",
    "berater",
}
STOP = {
    "job",
    "jobs",
    "position",
    "positions",
    "role",
    "roles",
    "in",
    "at",
    "for",
    "with",
    "and",
    "or",
    "a",
    "an",
    "the",
    "near",
    "around",
    "remote",
    "hybrid",
    "onsite",
    "looking",
    "want",
    "i",
    "m",
    "am",
    "stelle",
    "stellen",
    "im",
    "und",
    "mit",
}


def _rule_titles(text: str, place_words: set[str], keywords: list[str]) -> list[str]:
    known = glossary().find_titles(text)
    if known:
        return known[:3]
    drop = place_words | {k.lower() for k in keywords} | STOP
    parts = re.split(r",|;|\bor\b|\boder\b", text, flags=re.I)
    titles: list[str] = []
    for part in parts:
        ws = [w for w in re.findall(r"[\w+#/.&-]+", part) if w.lower() not in drop]
        if ws and (any(w.lower() in ROLE_NOUNS for w in ws) or len(ws) <= 4):
            title = " ".join(ws)
            titles.append(title[:1].upper() + title[1:])
    return [t for t in titles if t][:3]


def parse_rules(text: str) -> SearchIntent:
    found_places = places().find_all(text)
    place_words = {w.lower() for p in found_places for w in p.name.split()} | {"europe", "dach"}
    keywords = [h.term.name for h in glossary().find(text) if h.term.kind == "skill"][:5]
    titles = _rule_titles(text, place_words, keywords)
    return SearchIntent(titles=titles, places=found_places[:5], keywords=keywords, by_ai=False)


def _validate(data: dict[str, object], text: str, fallback: SearchIntent) -> SearchIntent:
    norm = normalize(text)
    raw_titles = data.get("titles") or []
    titles = [str(t).strip()[:60] for t in raw_titles if str(t).strip()]  # type: ignore[attr-defined]
    resolved: list[Place] = []
    for raw in data.get("places") or []:  # type: ignore[attr-defined]
        name = str(raw).strip()
        if not name:
            continue
        p = places().resolve(name)
        # only places the user wrote (by name or alias) are accepted
        written = normalize(name) in norm or any(
            normalize(fp.name) == normalize(p.name) for fp in fallback.places
        )
        if written and p not in resolved:
            resolved.append(p)
    keywords = []
    for raw in data.get("keywords") or []:  # type: ignore[attr-defined]
        k = str(raw).strip()
        if k and normalize(k) in norm:
            keywords.append(glossary().canonical(k)[:40])
    return SearchIntent(
        titles=titles[:3] or fallback.titles,
        places=resolved[:5] or fallback.places,
        keywords=list(dict.fromkeys(keywords))[:5] or fallback.keywords,
        by_ai=bool(titles),
    )


async def parse_search(text: str, settings: Settings) -> SearchIntent:
    fallback = parse_rules(text)
    gate = LLMGate(settings)
    data = await gate.call_json(
        [
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": f"<search>{text}</search>"},
        ],
        fast=True,
    )
    if not isinstance(data, dict):
        return fallback
    return _validate(data, text, fallback)
