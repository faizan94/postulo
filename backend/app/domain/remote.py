"""Is a remote job open to someone living in the user's country? (Phase 2, R6)

"Remote - US" or "Anywhere in the U.S." is not useful for a person in Berlin. A remote job is
kept when it names no country, names the user's country, or names a region that contains it
(Europe/EU/EMEA for Germany), or says worldwide/anywhere/global.
"""

import re

from app.domain.places import JobLocation, places

_WORLDWIDE = re.compile(
    r"\b(worldwide|anywhere(?! in)|global(ly)?|any location|all locations)\b", re.I
)
# Two-letter and dotted country forms the places list skips (too short to match safely).
_SHORT_COUNTRY = {
    "US": re.compile(r"(?<![\w.])(US|U\.S\.A?\.?|USA)(?![\w])"),
    "GB": re.compile(r"(?<![\w.])(UK|U\.K\.)(?![\w])"),
}


def _named_countries(text: str) -> set[str]:
    p = places()
    found = {code for code in p.countries if p.matches(JobLocation(text), p.country_place(code))}  # type: ignore[arg-type]
    for code, pat in _SHORT_COUNTRY.items():
        if pat.search(text):
            found.add(code)
    return found


def remote_ok_for(job: JobLocation, home_country: str | None) -> bool:
    """True if this remote job can plausibly be done from `home_country` (ISO code)."""
    if not job.remote or not home_country:
        return True
    text = job.text
    if _WORLDWIDE.search(text):
        return True
    countries = _named_countries(text)
    if job.country_code:
        countries.add(job.country_code.upper())
    if home_country in countries:
        return True
    p = places()
    for name, region in p.regions.items():
        if home_country in region["countries"] and p.matches(job, p.resolve(name)):
            return True
    # No country named at all ("Remote") -> keep; a different country named -> drop.
    return not countries
