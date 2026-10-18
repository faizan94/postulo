"""Search queries from titles and places (D17). LLM proposes; code validates; template fallback."""

from dataclasses import dataclass

from app.agents.llm_gate import LLMGate
from app.agents.prompts.plan import PLAN_SYSTEM_PROMPT
from app.domain.places import places
from app.domain.titles import tokens
from app.schemas.common import Place
from app.schemas.profile import Profile

MAX_QUERIES = 3
ANYWHERE = Place(kind="region", name="Anywhere")


@dataclass(frozen=True)
class Query:
    text: str
    place: Place
    country: str | None  # Tavily country boost


def _place_word(p: Place) -> str:
    return "remote" if p.kind == "remote" else p.name


def template_queries(
    titles: list[str], wanted: list[Place], keywords: list[str] | None = None
) -> list[Query]:
    """title x place queries; no places = Anywhere. Keywords go on the first query only."""
    out: list[Query] = []
    for p in wanted or [None]:  # type: ignore[list-item]
        for t in titles:
            where = _place_word(p) if p else ""
            out.append(Query(f"{t} {where}".strip(), p or ANYWHERE, None))
    if out and keywords:
        first = out[0]
        out[0] = Query(f"{first.text} {' '.join(keywords[:3])}", first.place, None)
    return out[:MAX_QUERIES]


async def plan_queries(
    titles: list[str],
    wanted: list[Place],
    profile: Profile,
    gate: LLMGate,
    keywords: list[str] | None = None,
) -> tuple[list[Query], bool]:
    """(queries, planned_by_llm)."""
    fallback = template_queries(titles, wanted, keywords)
    if not wanted:
        return fallback, False  # Anywhere: the template queries are already broad
    if not gate.usable:
        return fallback, False
    skills = ", ".join(s.name for s in profile.skills if s.type == "tech")[:200]
    data = await gate.call_json(
        [
            {"role": "system", "content": PLAN_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Titles: {titles}\nPlaces: {[_place_word(p) for p in wanted]}\n"
                    f"Top skills: {skills or 'n/a'}\n"
                    f"User keywords: {keywords or 'none'}"
                ),
            },
        ],
        reasoning="on",
    )
    if not isinstance(data, dict):
        return fallback, False
    by_word = {_place_word(p).lower(): p for p in wanted}
    title_words = [set(tokens(t)) for t in titles]
    queries: list[Query] = []
    for item in data.get("queries", []):
        if not isinstance(item, dict):
            continue
        text = str(item.get("query", "")).strip()
        place = by_word.get(str(item.get("place", "")).strip().lower())
        words = set(tokens(text))
        if not text or len(text) > 80 or place is None:
            continue
        if not any(tw <= words for tw in title_words if tw):
            continue  # must contain a requested title (code validates the LLM)
        queries.append(Query(text, place, places().tavily_country(place)))
    return (queries[:MAX_QUERIES], True) if queries else (fallback, False)
