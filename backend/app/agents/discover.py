"""Discover company boards with Tavily, expand them via board APIs, run the quiet checks.

Checks (cheapest first, D5): on the company's board (open) -> fresh -> right place -> right
title -> has text. Failures are only logged for the judge view; users never see them.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol

from app.agents.planner import Query
from app.domain.places import JobLocation, places
from app.domain.titles import title_matches
from app.schemas.common import Place
from app.services.ats import ATS_DOMAINS, BoardJob, BoardRef, detect
from app.services.tavily_client import SearchResult

log = logging.getLogger(__name__)

MAX_BOARDS_PER_ROUND = 12
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


async def discover(queries: list[Query], tavily: SearchLike, credit_budget: int) -> Discovery:
    d = Discovery()
    for q in queries:
        if d.credits >= credit_budget:
            break
        res = await tavily.search(
            q.text,
            include_domains=ATS_DOMAINS,
            time_range="month",
            max_results=10,
            country=q.country,
        )
        d.credits += res.credits
        if not res.results and q.country and d.credits < credit_budget:
            # Tavily occasionally returns nothing with a country boost; retry once without it.
            res = await tavily.search(
                q.text, include_domains=ATS_DOMAINS, time_range="month", max_results=10
            )
            d.credits += res.credits
        for r in res.results:
            ref = detect(str(r.get("url", "")))
            if ref is None:
                continue
            key = (ref.ats, ref.slug.lower(), ref.eu)
            if key not in d.refs and len(d.refs) < MAX_BOARDS_PER_ROUND:
                d.refs[key] = BoardRef(ref.ats, ref.slug, None, ref.eu)
            if ref.job_id and key in d.refs:
                d.found_jobs[str(r["url"])] = (ref, str(r.get("title") or "Job posting"))
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
            if j.url in seen_urls or not title_matches(j.title, titles):
                continue
            was_found = j.external_id in found_ids
            loc = JobLocation(j.location_text, j.country_code, j.remote)
            if not any(places().matches(loc, p) for p in wanted):
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
            if len(j.text) < MIN_TEXT_CHARS:
                dropped.append(Dropped(j.title, j.company, j.url, "no readable job text"))
                continue
            matches.append(Candidate(j, len(jobs), newest))
        matches.sort(key=lambda c: c.job.posted_at or date.min, reverse=True)
        kept.extend(matches[:MAX_PER_COMPANY])
    return kept, dropped
