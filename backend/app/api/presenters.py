"""DB rows -> API shapes. One place, so routes and the event stream render the same JSON."""

from typing import Any

from app.db.tables import Company, CvVersion, Posting, Search, SearchResult
from app.db.tables import User as UserRow
from app.schemas.auth import User
from app.schemas.common import Place
from app.schemas.cv import CvVersion as CvVersionOut
from app.schemas.posting import CompanyScore, JobCard, MatchScore, PostingDetail, SkillMatch
from app.schemas.search import (
    LearnNextItem,
    SearchDetail,
    SearchSummary,
    SkillSummaryItem,
)
from app.scoring.rank import rank_key

_PENDING = CompanyScore(value=None, band="pending")


def user_out(u: UserRow) -> User:
    return User(
        id=u.id,
        name=u.display_name,
        default_titles=list(u.default_titles or []),
        default_places=[Place.model_validate(p) for p in u.default_places or []],
    )


def cv_out(cv: CvVersion) -> CvVersionOut:
    return CvVersionOut(
        id=cv.id,
        label=cv.label,
        source_type=cv.source_type,  # type: ignore[arg-type]
        ocr_used=cv.ocr_used,
        status=cv.status,  # type: ignore[arg-type]
        created_at=cv.created_at,
        confirmed_at=cv.confirmed_at,
    )


def company_score(c: Company | None) -> CompanyScore:
    if c is None or c.band == "pending":
        return _PENDING
    return CompanyScore(
        value=round(c.score) if c.score is not None else None,
        band=c.band,  # type: ignore[arg-type]
        sources=(c.signals or {}).get("sources", []),
    )


def _place(p: Posting) -> Place | None:
    raw = (p.location or {}).get("place")
    return Place.model_validate(raw) if raw else None


def _match(breakdown: dict[str, Any]) -> MatchScore:
    m = breakdown.get("match")
    return MatchScore.model_validate(m) if m else MatchScore(must_met="0/0", nice_met="0/0")


def _skills(breakdown: dict[str, Any]) -> list[SkillMatch]:
    return [SkillMatch.model_validate(s) for s in breakdown.get("skills", [])]


_ORDER = {"missing_must": 0, "have": 1, "related": 2, "missing_nice": 3}


def top_skills(skills: list[SkillMatch]) -> list[SkillMatch]:
    """Six chips for a card: must-have gaps first, then strengths, then the rest."""
    must_first = sorted(
        skills,
        key=lambda s: (s.requirement.importance != "must", _ORDER[s.status]),
    )
    return must_first[:6]


def job_card(r: SearchResult, p: Posting, c: Company | None) -> JobCard:
    skills = _skills(r.breakdown)
    return JobCard(
        posting_id=p.id,
        title=p.title,
        company=c.name if c else p.board_slug,
        place=_place(p),
        workplace_type=p.workplace_type,  # type: ignore[arg-type]
        posted_at=p.posted_at,
        match=_match(r.breakdown),
        company_score=company_score(c),
        top_skills=top_skills(skills),
        related_role=r.breakdown.get("title_match") == "related",
    )


def posting_detail(r: SearchResult, p: Posting, c: Company | None) -> PostingDetail:
    return PostingDetail(
        posting_id=p.id,
        title=p.title,
        company=c.name if c else p.board_slug,
        place=_place(p),
        workplace_type=p.workplace_type,  # type: ignore[arg-type]
        posted_at=p.posted_at,
        url=p.url,
        apply_url=p.apply_url,
        full_text=p.full_text,
        match=_match(r.breakdown),
        skills=_skills(r.breakdown),
        company_score=company_score(c),
        related_role=r.breakdown.get("title_match") == "related",
    )


def search_summary(s: Search, result_count: int) -> SearchSummary:
    return SearchSummary(
        id=s.id,
        status=s.status,  # type: ignore[arg-type]
        cv_version_id=s.cv_version_id,
        titles=list(s.titles),
        places=[Place.model_validate(p) for p in s.places],
        keywords=list(s.keywords or []),
        related_titles=list(s.related_titles or []),
        result_count=result_count,
        created_at=s.created_at,
        finished_at=s.finished_at,
    )


def search_detail(
    s: Search, rows: list[tuple[SearchResult, Posting, Company | None]]
) -> SearchDetail:
    cards = [job_card(r, p, c) for r, p, c in rows]
    ranks = {r.posting_id: r.rank for r, _p, _c in rows}
    if all(ranks.get(card.posting_id) for card in cards):
        cards.sort(key=lambda card: ranks[card.posting_id] or 0)
    else:
        cards.sort(key=rank_key)
    summary = s.summary or {}
    base = search_summary(s, len(cards))
    return SearchDetail(
        **base.model_dump(),
        stage=s.stage,  # type: ignore[arg-type]
        note=s.note,
        error=s.error,
        results=cards,
        skill_summary=[SkillSummaryItem.model_validate(x) for x in summary.get("skills", [])],
        learn_next=[LearnNextItem.model_validate(x) for x in summary.get("learn_next", [])],
    )
