"""Profile x requirements -> skill statuses, by code (G8). Deterministic, so D6 holds."""

from app.domain.glossary import glossary
from app.domain.rules import CEFR
from app.schemas.common import Evidence
from app.schemas.posting import Requirement, SkillMatch, SkillStatus
from app.schemas.profile import Profile, SkillItem


def _level_ok(have: str | None, need: str | None) -> bool:
    """Unknown levels pass (gates skip null inputs). 'native' beats everything."""
    if need is None or have is None:
        return True
    try:
        return CEFR.index(have) >= CEFR.index(need)
    except ValueError:
        return True


def _missing(req: Requirement) -> SkillStatus:
    # A missing soft "must" still shows as missing_nice (§7.1).
    return "missing_must" if req.importance == "must" and req.type != "soft" else "missing_nice"


def match(profile: Profile, requirements: list[Requirement]) -> list[SkillMatch]:
    g = glossary()
    # Tokenized form: 'REACT', 'react' and 'React.js' are the same skill (domain/normalize.py).
    skills = {g.key_of(s.name): s for s in profile.skills}
    languages = {g.key_of(lang.name): lang for lang in profile.languages}
    out: list[SkillMatch] = []
    for req in requirements:
        status: SkillStatus
        evidence = None
        if req.type == "language":
            lang = languages.get(g.key_of(req.name))
            if lang and _level_ok(lang.level, req.level):
                status, evidence = "have", lang.evidence
            else:
                status = _missing(req)
        elif req.type == "years":
            years = profile.years_total
            ok = years is None or req.min_years is None or years >= req.min_years
            status = "have" if ok else _missing(req)
        elif req.type == "degree":
            status = "have" if profile.education else "missing_nice"
            evidence = profile.education[0].evidence if profile.education else None
        elif g.key_of(req.name) in skills:
            status, evidence = "have", skills[g.key_of(req.name)].evidence
        else:
            related = _related_skill(req.name, skills)
            if related is not None:
                status, evidence = "related", related.evidence
            else:
                status, evidence = _by_phrase(req, skills)
        out.append(SkillMatch(requirement=req, status=status, cv_evidence=evidence))
    return out


def _related_skill(name: str, skills: dict[str, SkillItem]) -> SkillItem | None:
    g = glossary()
    return next((skills[g.key_of(n)] for n in g.related_to(name) if g.key_of(n) in skills), None)


def _by_phrase(
    req: Requirement, skills: dict[str, SkillItem]
) -> tuple[SkillStatus, Evidence | None]:
    """Fallback for phrase-style names ("Fluency in Python", "LangChain or LangGraph"):
    the glossary skills inside the name decide. All of them in the CV -> have; some of them
    (or a related skill) -> close match; none -> missing."""
    hits = [h.term.name for h in glossary().find(req.name) if h.term.kind != "language"]
    have = [skills[k] for k in (glossary().key_of(n) for n in hits) if k in skills]
    if hits and len(have) == len(hits):
        return "have", have[0].evidence
    close = (
        have[0]
        if have
        else next((r for n in hits if (r := _related_skill(n, skills)) is not None), None)
    )
    if close is not None:
        return "related", close.evidence
    return _missing(req), None
