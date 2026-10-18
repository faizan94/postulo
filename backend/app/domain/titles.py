"""Does a job title match what the user wants? Token rules, seniority-agnostic."""

import re

SENIORITY = {
    "senior",
    "sr",
    "junior",
    "jr",
    "lead",
    "staff",
    "principal",
    "mid",
    "medior",
    "level",
    "i",
    "ii",
    "iii",
    "iv",
}
STUDENT = {
    "intern",
    "internship",
    "praktikum",
    "praktikant",
    "praktikantin",
    "werkstudent",
    "werkstudentin",
    "student",
    "trainee",
    "apprentice",
    "ausbildung",
    "thesis",
}
MANAGEMENT = {"manager", "director", "head", "vp", "chief", "leiter", "leiterin"}
SYNONYMS = [{"engineer", "developer", "entwickler", "entwicklerin", "engineering"}]
_NOISE = re.compile(r"\((?:[mwfdxa]\s*/\s*)+[mwfdxa]\)|\(all genders?\)|\(m/w/d\)", re.I)


def tokens(title: str) -> list[str]:
    t = _NOISE.sub(" ", title.lower())
    return [w for w in re.split(r"[^\wäöüß+#]+", t) if w]


def _same(a: str, b: str) -> bool:
    if a == b or b.startswith(a) or a.startswith(b) and len(b) >= 4:
        return True
    return any(a in g and b in g for g in SYNONYMS)


_JOIN = re.compile(r"\s*(?:&|/|\band\b|\bund\b|\+)\s*", re.I)


def variants(title: str) -> list[str]:
    """'Lead Data & AI Engineer' -> [itself, 'Lead Data Engineer', 'AI Engineer'].

    Compound titles rarely appear verbatim on boards, so each side is matched on its own,
    sharing the role noun ('Engineer') that comes last.
    """
    parts = [p for p in _JOIN.split(title) if p.strip()]
    if len(parts) < 2:
        return [title]
    noun = parts[-1].split()[-1]
    out = [title]
    for p in parts:
        words = p.split()
        out.append(p if words and words[-1].lower() == noun.lower() else f"{p} {noun}")
    return list(dict.fromkeys(out))


def family(wanted: list[str], limit: int = 8) -> list[str]:
    """Related role titles for the wanted titles (D20), from the glossary's role families.

    'Senior AI Engineer' -> family of 'AI Engineer' (Machine Learning Engineer, LLM Engineer...).
    """
    from app.domain.glossary import glossary  # local: glossary imports nothing from here

    g = glossary()
    wanted_l = {w.lower() for w in wanted}
    out: list[str] = []
    for w in wanted:
        bases = [w, *g.find_titles(w)]
        for v in variants(w):
            bases += g.find_titles(v)
        for base in bases:
            for r in g.related_titles(base):
                if r.lower() not in wanted_l and r not in out:
                    out.append(r)
    return out[:limit]


def match_kind(job_title: str, wanted: list[str], related: list[str]) -> str | None:
    """'exact' (the title the user asked for), 'related' (same role family) or None."""
    if title_matches(job_title, wanted):
        return "exact"
    if related and title_matches(job_title, related):
        return "related"
    return None


def title_matches(job_title: str, wanted: list[str]) -> bool:
    job = tokens(job_title)
    job_set = set(job)
    for w in [v for title in wanted for v in variants(title)]:
        want = [t for t in tokens(w) if t not in SENIORITY]
        if not want:
            continue
        if job_set & STUDENT and not set(want) & STUDENT:
            continue
        if job_set & MANAGEMENT and not set(want) & MANAGEMENT:
            continue
        if all(any(_same(t, j) for j in job) for t in want):
            return True
    return False
