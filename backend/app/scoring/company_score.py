"""Company score from public signals only (D7, §7.2). Core: hiring activity + basics."""

from dataclasses import dataclass
from datetime import date

HIRING_MAX = 50
BASICS_MAX = 20


@dataclass(frozen=True)
class CompanySignals:
    open_roles: int | None  # None: company not on a supported board
    newest_posted: date | None
    own_domain: str | None  # careers site on the company's own domain


def hiring_points(open_roles: int, newest: date | None, today: date) -> int:
    roles = 30 if open_roles >= 50 else 22 if open_roles >= 10 else 15 if open_roles >= 3 else 8
    if newest is None:
        fresh = 0
    else:
        age = (today - newest).days
        fresh = 20 if age <= 7 else 14 if age <= 30 else 7 if age <= 90 else 0
    return roles + fresh


def score(sig: CompanySignals, today: date | None = None) -> tuple[int | None, str]:
    """(value 0-100 or None, band)."""
    today = today or date.today()
    if sig.open_roles is None:
        return None, "not_enough_data"
    got = hiring_points(sig.open_roles, sig.newest_posted, today)
    available = HIRING_MAX
    if sig.own_domain:
        got += BASICS_MAX
        available += BASICS_MAX
    value = round(100 * got / available)
    band = "strong" if value >= 70 else "okay" if value >= 40 else "weak"
    return value, band
