"""Years of experience and seniority, computed by code (G3)."""

import re
from datetime import date

from app.schemas.profile import Role, Seniority

_PRESENT = r"present|current|now|today|heute|aktuell|jetzt|bis heute|laufend"
DATE_RANGE = re.compile(
    rf"(?P<s>(?:(?:0?[1-9]|1[0-2])[./])?(?:19|20)\d{{2}})\s*(?:-|–|—|to|bis)\s*"
    rf"(?P<e>(?:(?:0?[1-9]|1[0-2])[./])?(?:19|20)\d{{2}}|{_PRESENT})",
    re.IGNORECASE,
)
EDUCATION_WORDS = re.compile(
    r"universit|bachelor|master|b\.?\s?sc|m\.?\s?sc|phd|studium|hochschule|school|degree|"
    r"ausbildung|abitur|gymnasium|college",
    re.IGNORECASE,
)


def _parse(value: str, end: bool, today: date) -> tuple[int, int] | None:
    v = value.strip().lower()
    if re.fullmatch(_PRESENT, v):
        return today.year, today.month
    m = re.fullmatch(r"(?:(\d{1,2})[./])?(\d{4})", v)
    if not m:
        m2 = re.fullmatch(r"(\d{4})-(\d{2})", v)  # YYYY-MM (LLM roles)
        if not m2:
            return None
        return int(m2.group(1)), int(m2.group(2))
    month = int(m.group(1)) if m.group(1) else (7 if end else 6)  # year-only: mid-year
    return int(m.group(2)), month


def _months(intervals: list[tuple[tuple[int, int], tuple[int, int]]]) -> int:
    spans = sorted((s[0] * 12 + s[1], e[0] * 12 + e[1]) for s, e in intervals if e >= s)
    total, cur_s, cur_e = 0, None, None
    for s, e in spans:
        if cur_e is None or s > cur_e:
            if cur_e is not None and cur_s is not None:
                total += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None and cur_s is not None:
        total += cur_e - cur_s
    return total


def years_from_roles(roles: list[Role], today: date | None = None) -> float | None:
    today = today or date.today()
    intervals = []
    for r in roles:
        if not r.start:
            continue
        s = _parse(r.start, False, today)
        e = _parse(r.end or "present", True, today)
        if s and e:
            intervals.append((s, e))
    if not intervals:
        return None
    return round(_months(intervals) / 12, 1)


def ranges_in_text(text: str) -> list[tuple[str, str, str]]:
    """(start, end, line) for date ranges on work lines (education lines are skipped)."""
    out = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        for m in DATE_RANGE.finditer(line):
            context = (
                line
                + " "
                + (lines[i - 1] if i else "")
                + " "
                + (lines[i + 1] if i + 1 < len(lines) else "")
            )
            if EDUCATION_WORDS.search(context):
                continue
            out.append((m.group("s"), m.group("e"), line.strip()))
    return out


def seniority(years: float | None) -> Seniority | None:
    if years is None:
        return None
    if years < 2:
        return "junior"
    if years < 5:
        return "mid"
    if years < 9:
        return "senior"
    return "lead"
