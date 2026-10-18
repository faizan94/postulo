"""Match score 0-100 (§7.1). Starting weights; tune on real postings and record in the plan."""

from app.schemas.posting import MatchScore, SkillMatch
from app.schemas.profile import Profile

SCORED_TYPES = {"tech", "soft", "domain", "language"}
WEIGHT = {"must": 3, "nice": 1}
CREDIT = {"have": 1.0, "related": 0.5, "missing_nice": 0.0, "missing_must": 0.0}
LANGUAGE_CAP = 50
YEARS_CAP = 60
YEARS_SLACK = 2
MIN_REQUIREMENTS = 3


def _weight(m: SkillMatch) -> int:
    if m.requirement.type == "soft":
        return WEIGHT["nice"]
    return WEIGHT[m.requirement.importance]


def score(matches: list[SkillMatch], profile: Profile) -> MatchScore:
    scored = [m for m in matches if m.requirement.type in SCORED_TYPES]
    must = [
        m for m in scored if m.requirement.importance == "must" and m.requirement.type != "soft"
    ]
    nice = [m for m in scored if m not in must]
    must_met = f"{sum(m.status == 'have' for m in must)}/{len(must)}"
    nice_met = f"{sum(m.status == 'have' for m in nice)}/{len(nice)}"
    thin = len(matches) < MIN_REQUIREMENTS
    if not scored:
        return MatchScore(value=None, must_met=must_met, nice_met=nice_met, thin=True)

    total = sum(_weight(m) for m in scored)
    got = sum(_weight(m) * CREDIT[m.status] for m in scored)
    value = round(100 * got / total)
    gates: list[str] = []

    for m in matches:
        r = m.requirement
        if r.type == "language" and r.importance == "must" and m.status != "have":
            if value > LANGUAGE_CAP:
                value = LANGUAGE_CAP
            gates.append(f"{r.name}{' ' + r.level if r.level else ''} required")
        if (
            r.type == "years"
            and r.min_years is not None
            and profile.years_total is not None
            and r.min_years > profile.years_total + YEARS_SLACK
        ):
            value = min(value, YEARS_CAP)
            gates.append(f"{r.min_years:g}+ years required")
    return MatchScore(
        value=value, must_met=must_met, nice_met=nice_met, gates_applied=gates, thin=thin
    )
