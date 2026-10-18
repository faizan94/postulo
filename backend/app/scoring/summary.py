"""Skill summary and Gap ROI across the shown jobs (§7.3). No LLM calls."""

from collections import defaultdict
from typing import Literal

from app.domain.glossary import glossary
from app.schemas.posting import SkillMatch
from app.schemas.profile import Profile
from app.schemas.search import LearnNextItem, SkillSummaryItem
from app.scoring.match_score import score

LEARNABLE = {"tech", "domain", "language"}
UserStatus = Literal["have", "related", "missing"]
_ORDER: dict[UserStatus, int] = {"have": 0, "related": 1, "missing": 2}


def skill_summary(jobs: list[list[SkillMatch]]) -> list[SkillSummaryItem]:
    """Demand per skill across jobs, grouped by key so 'React' and 'REACT' are one bar."""
    g = glossary()
    label: dict[str, str] = {}
    demand: dict[str, int] = defaultdict(int)
    must: dict[str, int] = defaultdict(int)
    status: dict[str, UserStatus] = {}
    for skills in jobs:
        seen: set[str] = set()
        for m in skills:
            r = m.requirement
            if r.type in ("years", "degree"):
                continue
            k = g.key_of(r.name)
            if k in seen:  # one job counts once per skill
                continue
            seen.add(k)
            label.setdefault(k, g.canonical(r.name))
            demand[k] += 1
            must[k] += r.importance == "must"
            user: UserStatus = (
                "have" if m.status == "have" else "related" if m.status == "related" else "missing"
            )
            # the best status seen wins (a skill can be 'related' in one job, 'have' in another)
            if k not in status or _ORDER[user] < _ORDER[status[k]]:
                status[k] = user
    total = len(jobs)
    items = [
        SkillSummaryItem(
            skill=label[k], user_status=status[k], demand=n, of=total, must_count=must[k]
        )
        for k, n in demand.items()
    ]
    return sorted(items, key=lambda i: (-i.demand, -i.must_count, i.skill))[:20]


def learn_next(jobs: list[list[SkillMatch]], profile: Profile, top: int = 3) -> list[LearnNextItem]:
    """For each missing learnable skill: what if you had it? Re-score every job (by key)."""
    g = glossary()
    candidates: dict[str, tuple[str, str]] = {}  # key -> (label, type)
    for skills in jobs:
        for m in skills:
            if m.status in ("missing_must", "missing_nice") and m.requirement.type in LEARNABLE:
                k = g.key_of(m.requirement.name)
                candidates.setdefault(k, (g.canonical(m.requirement.name), m.requirement.type))

    def is_gap(m: SkillMatch, k: str) -> bool:
        return m.status.startswith("missing") and g.key_of(m.requirement.name) == k

    items: list[LearnNextItem] = []
    for k, (name, req_type) in candidates.items():
        improved, gains, unlocks = 0, [], 0
        for skills in jobs:
            if not any(is_gap(m, k) for m in skills):
                continue
            before = score(skills, profile)
            after = score(
                [m.model_copy(update={"status": "have"}) if is_gap(m, k) else m for m in skills],
                profile,
            )
            if before.value is None or after.value is None:
                continue
            gain = after.value - before.value
            if gain > 0:
                improved += 1
                gains.append(gain)
            had_must_miss = any(is_gap(m, k) and m.status == "missing_must" for m in skills)
            if had_must_miss or len(after.gates_applied) < len(before.gates_applied):
                unlocks += 1
        if improved:
            items.append(
                LearnNextItem(
                    skill=name,
                    jobs_improved=improved,
                    avg_gain_points=round(sum(gains) / len(gains), 1),
                    unlocks=unlocks,
                    slow=req_type == "language",
                )
            )
    items.sort(key=lambda i: (-i.jobs_improved * i.avg_gain_points, -i.unlocks, i.skill))
    return items[:top]
