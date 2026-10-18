"""Discover company boards with Tavily, expand them via board APIs, run the quiet checks.

Checks (cheapest first, D5): on the company's board (open) -> fresh -> right place -> right
title -> has text. Failures are only logged for the trace view; users never see them.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol

from app.agents.planner import Query
from app.domain.places import JobLocation, places
from app.domain.remote import remote_ok_for
from app.domain.titles import match_kind
from app.schemas.common import Place
from app.services.ats import ATS_DOMAINS, BoardJob, BoardRef, detect
from app.services.tavily_client import SearchResult

log = logging.getLogger(__name__)

MAX_BOARDS_PER_ROUND = 8
MAX_PER_COMPANY = 3
MIN_TEXT_CHARS = 200


class SearchLike(Protocol):
    async def search(
        self,
        query: str,
        *,
        include_domains: list[str] | None = ...,
        time_range: str | None = ...,
        max_results: int = ...,
        country: str | None = ...,
    ) -> SearchResult: ...


class BoardsLike(Protocol):
    async def jobs(self, ref: BoardRef) -> list[BoardJob] | None: ...

    async def fill_text(self, job: BoardJob) -> None: ...


@dataclass
class Dropped:
    title: str
    company: str | None
    url: str
    reason: str


@dataclass
class Discovery:
    refs: dict[tuple[str, str, bool], BoardRef] = field(default_factory=dict)
    found_jobs: dict[str, tuple[BoardRef, str]] = field(default_factory=dict)  # url -> (ref, title)
    credits: int = 0


@dataclass
class Candidate:
    job: BoardJob
    board_size: int
    newest_on_board: date | None
    title_match: str = "exact"  # exact | related (D20)


def _mentions_place(result: dict[str, object], wanted: list[Place]) -> bool:
    text = " ".join(str(result.get(k) or "") for k in ("title", "content", "url"))
    loc = JobLocation(text, None, "remote" in text.lower())
    return any(places().matches(loc, p) for p in wanted)


async def discover(
    queries: list[Query], tavily: SearchLike, credit_budget: int, wanted: list[Place] | None = None
) -> Discovery:
    """Tavily finds company boards. Boards whose hits mention the user's place come first."""
    d = Discovery()
    order: dict[tuple[str, str, bool], tuple[int, int]] = {}  # key -> (mentions place, first seen)
    refs: dict[tuple[str, str, bool], BoardRef] = {}
    found: dict[str, tuple[tuple[str, str, bool], BoardRef, str]] = {}
    for q in queries:
        if d.credits >= credit_budget:
            break
        # No `country` boost: tested live, it often returned zero results together with
        # include_domains (costing a retry). The place is in the query text instead.
        res = await tavily.search(
            q.text, include_domains=ATS_DOMAINS, time_range="month", max_results=10
        )
        d.credits += res.credits
        for r in res.results:
            ref = detect(str(r.get("url", "")))
            if ref is None:
                continue
            key = (ref.ats, ref.slug.lower(), ref.eu)
            mentions = 1 if wanted and _mentions_place(r, wanted) else 0
            seen = order.get(key)
            order[key] = (max(mentions, seen[0] if seen else 0), seen[1] if seen else len(order))
            refs.setdefault(key, BoardRef(ref.ats, ref.slug, None, ref.eu))
            if ref.job_id:
                found[str(r["url"])] = (key, ref, str(r.get("title") or "Job posting"))
    best = sorted(order, key=lambda k: (-order[k][0], order[k][1]))[:MAX_BOARDS_PER_ROUND]
    d.refs = {k: refs[k] for k in best}
    d.found_jobs = {url: (ref, title) for url, (key, ref, title) in found.items() if key in d.refs}
    return d


def _same_job(job: BoardJob, ref: BoardRef) -> bool:
    return job.external_id == ref.job_id or job.url.endswith(f"/{ref.job_id}")


async def expand(
    d: Discovery,
    boards: BoardsLike,
    titles: list[str],
    wanted: list[Place],
    recent_days: int,
    seen_urls: set[str],
    today: date | None = None,
    related: list[str] | None = None,
    home_country: str | None = None,
) -> tuple[list[Candidate], list[Dropped]]:
    today = today or date.today()
    cutoff = today - timedelta(days=recent_days)
    sem = asyncio.Semaphore(6)

    async def load(ref: BoardRef) -> tuple[BoardRef, list[BoardJob] | None]:
        async with sem:
            return ref, await boards.jobs(ref)

    loaded = await asyncio.gather(*(load(r) for r in d.refs.values()))
    by_board = {(r.ats, r.slug.lower(), r.eu): jobs for r, jobs in loaded}
    kept: list[Candidate] = []
    dropped: list[Dropped] = []

    # Quiet check 1: jobs Tavily found must still be on their company's board.
    for url, (ref, title) in d.found_jobs.items():
        jobs = by_board.get((ref.ats, ref.slug.lower(), ref.eu))
        if jobs is None:
            dropped.append(Dropped(title, ref.slug, url, "board could not be read"))
        elif not any(_same_job(j, ref) for j in jobs):
            dropped.append(
                Dropped(title, ref.slug, url, "closed: no longer on the company's board")
            )

    for ref, jobs in loaded:
        if not jobs:
            continue
        newest = max((j.posted_at for j in jobs if j.posted_at), default=None)
        found_ids = {fr.job_id for fr, _t in d.found_jobs.values() if fr.slug == ref.slug}
        matches: list[Candidate] = []
        for j in jobs:
            kind = match_kind(j.title, titles, related or [])
            if j.url in seen_urls or kind is None:
                continue
            was_found = j.external_id in found_ids
            loc = JobLocation(j.location_text, j.country_code, j.remote)
            onsite_wanted = [p for p in wanted if p.kind != "remote"]
            via_remote_only = not any(places().matches(loc, p) for p in onsite_wanted)
            if (
                any(p.kind == "remote" for p in wanted)
                and via_remote_only
                and not remote_ok_for(
                    JobLocation(f"{j.location_text} {j.title}", j.country_code, j.remote),
                    home_country,
                )
                # titles often carry the restriction: "... (Anywhere in the U.S.)"
            ):
                if was_found or kind == "exact":
                    dropped.append(
                        Dropped(
                            j.title,
                            j.company,
                            j.url,
                            f"remote, but only for another country: {j.location_text}",
                        )
                    )
                continue
            if not places().matches_any(loc, wanted):
                if was_found:
                    dropped.append(
                        Dropped(
                            j.title,
                            j.company,
                            j.url,
                            f"wrong place: {j.location_text or 'unknown'}",
                        )
                    )
                continue
            if j.posted_at is not None and j.posted_at < cutoff:
                dropped.append(
                    Dropped(
                        j.title,
                        j.company,
                        j.url,
                        f"stale: posted {(today - j.posted_at).days} days ago",
                    )
                )
                continue
            matches.append(Candidate(j, len(jobs), newest, kind))
        # exact titles first, then newest
        matches.sort(
            key=lambda c: (c.title_match == "exact", c.job.posted_at or date.min), reverse=True
        )
        shortlist = matches[: MAX_PER_COMPANY + 1]

        async def fill(c: Candidate) -> None:
            async with sem:
                await boards.fill_text(c.job)

        await asyncio.gather(*(fill(c) for c in shortlist))
        with_text = []
        for c in shortlist:
            if len(c.job.text) < MIN_TEXT_CHARS:
                dropped.append(
                    Dropped(c.job.title, c.job.company, c.job.url, "no readable job text")
                )
            else:
                with_text.append(c)
        kept.extend(with_text[:MAX_PER_COMPANY])
    return kept, dropped
