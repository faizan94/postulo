"""Searches and their results."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import Company, Posting, Search, SearchResult, utcnow
from app.errors import NotFoundError


async def create(
    s: AsyncSession,
    user_id: int,
    cv_version_id: int,
    titles: list[str],
    places: list[dict[str, Any]],
    keywords: list[str] | None = None,
) -> Search:
    search = Search(
        user_id=user_id,
        cv_version_id=cv_version_id,
        titles=titles,
        places=places,
        keywords=list(keywords or []),
        related_titles=[],
        status="queued",
        trace=[],
        dropped=[],
        usage={},
    )
    s.add(search)
    await s.flush()
    return search


async def get_owned(s: AsyncSession, user_id: int, search_id: int) -> Search:
    search = await s.get(Search, search_id)
    if search is None or search.user_id != user_id:
        raise NotFoundError("Search not found.")
    return search


async def list_for_user(s: AsyncSession, user_id: int, limit: int = 50) -> list[Search]:
    rows = await s.scalars(
        select(Search)
        .where(Search.user_id == user_id)
        .order_by(Search.created_at.desc(), Search.id.desc())
        .limit(limit)
    )
    return list(rows)


async def latest_id(s: AsyncSession, user_id: int) -> int | None:
    return await s.scalar(
        select(Search.id)
        .where(Search.user_id == user_id)
        .order_by(Search.created_at.desc(), Search.id.desc())
        .limit(1)
    )


async def result_counts(s: AsyncSession, search_ids: list[int]) -> dict[int, int]:
    if not search_ids:
        return {}
    rows = await s.execute(
        select(SearchResult.search_id, func.count())
        .where(SearchResult.search_id.in_(search_ids))
        .group_by(SearchResult.search_id)
    )
    return {int(sid): int(n) for sid, n in rows.all()}


async def upsert_result(
    s: AsyncSession,
    search_id: int,
    posting_id: int,
    match_score: float | None,
    breakdown: dict[str, Any],
) -> None:
    row = await s.get(SearchResult, (search_id, posting_id))
    if row is None:
        s.add(
            SearchResult(
                search_id=search_id,
                posting_id=posting_id,
                match_score=match_score,
                breakdown=breakdown,
            )
        )
    else:
        row.match_score = match_score
        row.breakdown = breakdown


async def results_with_rows(
    s: AsyncSession, search_id: int
) -> list[tuple[SearchResult, Posting, Company | None]]:
    rows = await s.execute(
        select(SearchResult, Posting, Company)
        .join(Posting, Posting.id == SearchResult.posting_id)
        .outerjoin(Company, Company.id == Posting.company_id)
        .where(SearchResult.search_id == search_id)
    )
    return [(r, p, c) for r, p, c in rows.all()]


async def get_result(s: AsyncSession, search_id: int, posting_id: int) -> SearchResult | None:
    return await s.get(SearchResult, (search_id, posting_id))


async def set_ranks(s: AsyncSession, search_id: int, ordered_posting_ids: list[int]) -> None:
    keep = set(ordered_posting_ids)
    for row, _p, _c in await results_with_rows(s, search_id):
        if row.posting_id not in keep:
            await s.delete(row)
    for rank, pid in enumerate(ordered_posting_ids, start=1):
        result = await s.get(SearchResult, (search_id, pid))
        if result is not None:
            result.rank = rank


async def finish(s: AsyncSession, search: Search, status: str, error: str | None = None) -> None:
    search.status = status
    search.error = error
    search.finished_at = utcnow()
