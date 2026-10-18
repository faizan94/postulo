"""Verify agent: is the company real, is the posting still live, is it recent?

Drops ghost jobs (closed/dead links, stale reposts, unknown companies) and says why.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import httpx

from app.agents.search_agent import RawPosting
from app.models.schemas import RejectedPosting, VerifiedFlags
from app.services.tavily_client import ATS_DOMAINS, TavilyService

log = logging.getLogger(__name__)

RECENT_DAYS = 45
CLOSED_MARKERS = (
    "no longer accepting applications",
    "no longer available",
    "position has been filled",
    "job not found",
    "this job has expired",
    "job you are looking for",
    "page not found",
)
USER_AGENT = "Mozilla/5.0 (compatible; PostuloBot/0.1; +https://github.com/)"


@dataclass
class VerifiedPosting:
    raw: RawPosting
    flags: VerifiedFlags
    notes: list[str]


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)  # Tavily often returns RFC 2822 dates
        except (TypeError, ValueError):
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def is_recent(published: str | None, now: datetime | None = None) -> tuple[bool, str | None]:
    dt = parse_date(published)
    if dt is None:
        # Search is already restricted to the last month, so unknown dates pass.
        return True, "no posting date; search was limited to the last month"
    now = now or datetime.now(UTC)
    return now - dt <= timedelta(days=RECENT_DAYS), None


async def check_live(http: httpx.AsyncClient, url: str) -> tuple[bool, str | None]:
    try:
        resp = await http.get(url)
    except httpx.HTTPError as e:
        return False, f"could not load posting ({type(e).__name__})"
    if resp.status_code in (401, 403, 429):
        return True, f"site blocked the check (HTTP {resp.status_code}), assuming live"
    if resp.status_code >= 400:
        return False, f"posting returns HTTP {resp.status_code}"
    body = resp.text[:200_000].lower()
    for marker in CLOSED_MARKERS:
        if marker in body:
            return False, f"page says '{marker}'"
    final_path = [x for x in urlparse(str(resp.url)).path.split("/") if x]
    if len(final_path) <= 1 and len([x for x in urlparse(url).path.split("/") if x]) > 1:
        return False, "redirects to the job board index (posting removed)"
    return True, None


async def check_company(tavily: TavilyService, company: str | None) -> bool:
    if not company:
        return False
    results = await tavily.search(f'"{company}" company', max_results=3)
    for r in results:
        host = urlparse(r.get("url", "")).netloc.lower()
        if not any(d in host for d in ATS_DOMAINS):
            return True
    return False


async def verify_postings(
    postings: list[RawPosting], tavily: TavilyService
) -> tuple[list[VerifiedPosting], list[RejectedPosting]]:
    companies = {p.company for p in postings if p.company}
    sem = asyncio.Semaphore(5)

    async def company_task(name: str) -> tuple[str, bool]:
        async with sem:
            try:
                return name, await check_company(tavily, name)
            except Exception as e:  # one bad lookup must not kill the run
                log.warning("Company check failed for %s: %s", name, e)
                return name, True

    company_ok = dict(await asyncio.gather(*(company_task(c) for c in companies)))

    async with httpx.AsyncClient(
        timeout=10, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    ) as http:

        async def live_task(p: RawPosting) -> tuple[bool, str | None]:
            async with sem:
                return await check_live(http, p.url)

        live_results = await asyncio.gather(*(live_task(p) for p in postings))

    kept: list[VerifiedPosting] = []
    rejected: list[RejectedPosting] = []
    for p, (live, live_note) in zip(postings, live_results, strict=True):
        recent, recent_note = is_recent(p.published_date)
        flags = VerifiedFlags(
            company_exists=company_ok.get(p.company or "", False),
            posting_live=live,
            recent=recent,
        )
        notes = [n for n in (live_note, recent_note) if n]
        reason = None
        if not flags.posting_live:
            reason = live_note or "posting is not live"
        elif not flags.company_exists:
            reason = "could not confirm the company exists"
        elif not flags.recent:
            reason = f"older than {RECENT_DAYS} days (likely a repost or ghost job)"
        if reason:
            rejected.append(
                RejectedPosting(title=p.title, company=p.company, url=p.url, reason=reason)
            )
        else:
            kept.append(VerifiedPosting(raw=p, flags=flags, notes=notes))
    return kept, rejected
