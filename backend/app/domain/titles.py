"""Does a job title match what the user wants? Token rules, seniority-agnostic."""

import re

from app.domain.normalize import title_tokens

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
# (word in the wanted title, word in the job title that makes it a different role)
DIFFERENT_ROLE_PAIRS = [("react", "native")]
SYNONYMS = [
    {
        "engineer",
        "developer",
        "entwickler",
        "entwicklerin",
        "engineering",
        "ingenieur",
        "ingenieurin",
        "programmer",
        "programmierer",
    },
    {"data", "daten"},
    {"analyst", "analystin", "analytiker"},
    {"architect", "architekt", "architektin"},
    {"scientist", "wissenschaftler"},
    {"consultant", "berater", "beraterin"},
    {"manager", "managerin"},
]


def tokens(title: str) -> list[str]:
    """Normalized title tokens (see domain/normalize.py: case, gender marks, German compounds,
    abbreviations like 'Sr.'/'Eng', and variants like 'Front-End'/'Full Stack' are unified)."""
    return title_tokens(title)


def _same(a: str, b: str) -> bool:
    """Same word, a prefix of 4+ letters ('engineer' ~ 'engineering'), or a synonym.

    Short words must match exactly, so 'AI' never matches 'Airline'.
    """
    if a == b:
        return True
    if (len(a) >= 4 and b.startswith(a)) or (len(b) >= 4 and a.startswith(b)):
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

    def norm(t: str) -> str:
        return " ".join(tokens(t))

    wanted_keys = {norm(w) for w in wanted}
    out: list[str] = []
    for w in wanted:
        # A glossary title is a base when all its normalized tokens are in the wanted title:
        # 'Sr. AI Eng', 'AI-Engineer' and 'Lead Data & AI Engineer' all reach 'AI Engineer'.
        bases = [known for known in g.titles if title_matches(w, [known])]
        for base in bases:
            for r in g.related_titles(base):
                if norm(r) not in wanted_keys and norm(r) not in {norm(o) for o in out}:
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
        # A different job that shares a word: "React Native Developer" (mobile) is not a
        # "React Developer" (web), the same rule the skill glossary applies (D25).
        if any(a in want and b in job_set and b not in want for a, b in DIFFERENT_ROLE_PAIRS):
            continue
        if all(any(_same(t, j) for j in job) for t in want):
            return True
    return False
