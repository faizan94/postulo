"""Rule-based, grounded extraction (no LLM): posting requirements and a CV profile.

Used when the LLM is unavailable (mock mode, no budget, errors) and to back up the LLM so
glossary skills are never lost. Every quote is a verbatim substring of the source (G2).
"""

import re

from app.domain.evidence import snippet
from app.domain.glossary import glossary
from app.domain.places import places
from app.domain.years import ranges_in_text, seniority, years_from_roles
from app.schemas.common import Evidence
from app.schemas.posting import Importance, Requirement
from app.schemas.profile import EducationItem, LanguageItem, Profile, Role, SkillItem

CEFR = ["A1", "A2", "B1", "B2", "C1", "C2", "native"]
_LEVEL_WORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(native|mother tongue|muttersprach\w*|first language)\b", re.I), "native"),
    (re.compile(r"\b([ABC][12])\b"), ""),  # explicit CEFR, filled from the match
    (
        re.compile(
            r"\b(fluent\w*|flie(?:ß|ss)end\w*|verhandlungssicher\w*|business[- ]level|"
            r"proficient|excellent|sehr gut\w*|full professional)\b",
            re.I,
        ),
        "C1",
    ),
    (re.compile(r"\b(good|gute?n?|solid|conversational|working knowledge)\b", re.I), "B2"),
    (re.compile(r"\b(basic|grundkenntnisse|elementary|beginner)\b", re.I), "A2"),
]

_MUST_HEADERS = re.compile(
    r"requirement|qualification|what you bring|what we.?re looking for|you have|your profile|"
    r"who you are|must[- ]have|about you|you bring|we expect|skills|experience|"
    r"dein profil|ihr profil|anforderung|was du mitbringst|was sie mitbringen|qualifikation|"
    r"what you need|you should have|you will need",
    re.I,
)
_NICE_HEADERS = re.compile(
    r"nice[- ]to[- ]have|bonus|plus|preferred|ideally|wünschenswert|von vorteil|idealerweise|"
    r"pluspunkt|good to have",
    re.I,
)
_SKIP_HEADERS = re.compile(
    r"benefit|we offer|what we offer|wir bieten|perks|about us|über uns|who we are|why join|"
    r"what.?s in it for you|compensation|salary|equal opportunit|diversity|how to apply|"
    r"our values|the team|das bieten wir",
    re.I,
)
_TASK_HEADERS = re.compile(
    r"responsibilit|what you.?ll do|your tasks|your role|the role|deine aufgaben|ihre aufgaben|"
    r"what you will do|in this role|your mission|day to day",
    re.I,
)
_NICE_LINE = re.compile(
    r"nice[- ]to[- ]have|\bbonus\b|\ba plus\b|is a plus|\bplus\b|preferred|ideally|"
    r"von vorteil|wünschenswert|idealerweise|good to have|would be great",
    re.I,
)
_MUST_LINE = re.compile(
    r"\bmust\b|\brequired\b|essential|mandatory|zwingend|erforderlich|vorausgesetzt", re.I
)
_YEARS = re.compile(
    r"(?:at least|minimum of|min\.?|mindestens)?\s*(\d{1,2})\s*\+?\s*(?:\+\s*)?"
    r"(?:years?|yrs|jahre[n]?)(?!\s*old)",
    re.I,
)
_DEGREE = re.compile(
    r"\b(bachelor\w*|master\w*|ph\.?d|doctorate|degree|studium|hochschulabschluss|"
    r"universitätsabschluss|b\.?\s?sc|m\.?\s?sc)\b",
    re.I,
)


def language_level(text: str) -> str | None:
    for pat, level in _LEVEL_WORDS:
        m = pat.search(text)
        if m:
            return level or m.group(1).upper()
    return None


def _is_header(line: str) -> bool:
    s = line.strip()
    return 0 < len(s) <= 70 and (s.endswith(":") or len(s.split()) <= 8) and not s.endswith(".")


def _lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.strip()]


def extract_requirements(text: str) -> list[Requirement]:
    """Requirements of one posting, with section-aware must/nice and verbatim quotes."""
    g = glossary()
    found: dict[str, Requirement] = {}
    # Before any header the text is usually the company intro: only tools count (as nice).
    mode = "intro"
    max_years: tuple[float, str, Importance] | None = None

    def add(req: Requirement) -> None:
        old = found.get(req.name)
        if old is None or (old.importance == "nice" and req.importance == "must"):
            found[req.name] = req

    for line in _lines(text):
        hits = g.find(line)
        if _is_header(line):
            new_mode = None
            if _NICE_HEADERS.search(line):
                new_mode = "nice"
            elif _SKIP_HEADERS.search(line):
                new_mode = "skip"
            elif _TASK_HEADERS.search(line):
                new_mode = "task"
            elif _MUST_HEADERS.search(line):
                new_mode = "must"
            if new_mode:
                mode = new_mode
                if not hits:  # a pure header; "Nice to have: Kafka" still counts Kafka
                    continue
        if mode == "skip":
            continue
        importance: Importance = "must" if mode == "must" else "nice"
        if _NICE_LINE.search(line):
            importance = "nice"
        elif _MUST_LINE.search(line) and mode != "task":
            importance = "must"

        for hit in hits:
            if mode == "intro" and (hit.term.kind != "skill" or hit.term.type != "tech"):
                continue  # "...ranging from Marketing, Sales, Data" is not a requirement
            quote = snippet(line, hit.start, hit.end)
            if hit.term.kind == "language":
                add(
                    Requirement(
                        name=hit.term.name,
                        type="language",
                        importance=importance,
                        level=language_level(line),
                        evidence=Evidence(quote=quote),
                    )
                )
            else:
                add(
                    Requirement(
                        name=hit.term.name,
                        type="soft" if hit.term.kind == "soft" else hit.term.type,  # type: ignore[arg-type]
                        importance=importance,
                        evidence=Evidence(quote=quote),
                    )
                )
        for m in _YEARS.finditer(line):
            n = float(m.group(1))
            if 0 < n <= 20 and (max_years is None or n > max_years[0]):
                max_years = (n, snippet(line, m.start(1), m.end()), importance)
        dm = _DEGREE.search(line)
        if dm and mode in ("must", "nice"):
            add(
                Requirement(
                    name="Degree",
                    type="degree",
                    importance=importance,
                    evidence=Evidence(quote=snippet(line, dm.start(), dm.end())),
                )
            )
    if max_years:
        add(
            Requirement(
                name="Experience",
                type="years",
                importance=max_years[2],
                min_years=max_years[0],
                evidence=Evidence(quote=max_years[1]),
            )
        )
    return list(found.values())


def extract_profile(text: str) -> Profile:
    """A grounded profile from CV text using the glossary and date ranges only."""
    g = glossary()
    skills: dict[str, SkillItem] = {}
    langs: dict[str, LanguageItem] = {}
    education: list[EducationItem] = []
    for line in _lines(text):
        for hit in g.find(line):
            quote = snippet(line, hit.start, hit.end)
            if hit.term.kind == "language":
                langs.setdefault(
                    hit.term.name,
                    LanguageItem(
                        name=hit.term.name,
                        level=language_level(line),
                        evidence=Evidence(quote=quote),
                    ),
                )
            elif hit.term.name not in skills:
                skills[hit.term.name] = SkillItem(
                    name=hit.term.name,
                    type="soft" if hit.term.kind == "soft" else hit.term.type,  # type: ignore[arg-type]
                    evidence=Evidence(quote=quote),
                )
        dm = _DEGREE.search(line)
        if dm and len(education) < 4:
            education.append(
                EducationItem(
                    school=line.strip()[:120],
                    degree=dm.group(1),
                    evidence=Evidence(quote=line.strip()),
                )
            )

    roles = [
        Role(title=line[:120], company="", start=s, end=e, evidence=Evidence(quote=line))
        for s, e, line in ranges_in_text(text)
    ]
    years = years_from_roles(roles)
    titles = g.find_titles(text)[:3]
    return Profile(
        headline=titles[0] if titles else None,
        skills=list(skills.values()),
        roles=roles,
        languages=list(langs.values()),
        education=education,
        place=places().find_city(text),
        years_total=years,
        seniority=seniority(years),
        target_titles=titles,
    )
