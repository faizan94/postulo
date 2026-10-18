"""Skill summary and Gap ROI across the shown jobs (§7.3). No LLM calls."""

from collections import defaultdict
from typing import Literal

from app.schemas.posting import SkillMatch
from app.schemas.profile import Profile
from app.schemas.search import LearnNextItem, SkillSummaryItem
from app.scoring.match_score import score

LEARNABLE = {"tech", "domain", "language"}
UserStatus = Literal["have", "related", "missing"]
_ORDER: dict[UserStatus, int] = {"have": 0, "related": 1, "missing": 2}


def skill_summary(jobs: list[list[SkillMatch]]) -> list[SkillSummaryItem]:
    demand: dict[str, int] = defaultdict(int)
    must: dict[str, int] = defaultdict(int)
    status: dict[str, UserStatus] = {}
    for skills in jobs:
        for m in skills:
            r = m.requirement
            if r.type in ("years", "degree"):
                continue
            demand[r.name] += 1
            must[r.name] += r.importance == "must"
            user: UserStatus = (
                "have" if m.status == "have" else "related" if m.status == "related" else "missing"
            )
            # the best status seen wins (a skill can be 'related' in one job, 'have' in another)
            if r.name not in status or _ORDER[user] < _ORDER[status[r.name]]:
                status[r.name] = user
    total = len(jobs)
    items = [
        SkillSummaryItem(
            skill=name,
            user_status=status[name],
            demand=n,
            of=total,
            must_count=must[name],
        )
        for name, n in demand.items()
    ]
    return sorted(items, key=lambda i: (-i.demand, -i.must_count, i.skill))[:20]


def learn_next(jobs: list[list[SkillMatch]], profile: Profile, top: int = 3) -> list[LearnNextItem]:
    """For each missing learnable skill: what if you had it? Re-score every job."""
    candidates: dict[str, str] = {}
    for skills in jobs:
        for m in skills:
            if m.status in ("missing_must", "missing_nice") and m.requirement.type in LEARNABLE:
                candidates[m.requirement.name] = m.requirement.type
    items: list[LearnNextItem] = []
    for name, req_type in candidates.items():
        improved, gains, unlocks = 0, [], 0
        for skills in jobs:
            if not any(
                m.requirement.name == name and m.status.startswith("missing") for m in skills
            ):
                continue
            before = score(skills, profile)
            after_skills = [
                m.model_copy(update={"status": "have"})
                if m.requirement.name == name and m.status.startswith("missing")
                else m
                for m in skills
            ]
            after = score(after_skills, profile)
            if before.value is None or after.value is None:
                continue
            gain = after.value - before.value
            if gain > 0:
                improved += 1
                gains.append(gain)
            had_must_miss = any(
                m.requirement.name == name and m.status == "missing_must" for m in skills
            )
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
