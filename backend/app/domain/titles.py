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


def title_matches(job_title: str, wanted: list[str]) -> bool:
    job = tokens(job_title)
    job_set = set(job)
    for w in wanted:
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
