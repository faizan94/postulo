"""Job boards: Greenhouse, Lever and Ashby public APIs (free, no key).

A job on its company's board list is open; anything else is closed (G7). The board API also
gives the posting date, location, apply link and full text, so no page scraping is needed.
"""

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse

import httpx

from app.services.html_text import html_to_text

log = logging.getLogger(__name__)

Ats = Literal["greenhouse", "lever", "ashby"]
BOARD_CACHE_SECONDS = 6 * 3600
USER_AGENT = "PostuloBot/0.2 (job search assistant)"

# Tavily include_domains: only boards we can verify through their API.
ATS_DOMAINS = [
    "job-boards.greenhouse.io",
    "boards.greenhouse.io",
    "job-boards.eu.greenhouse.io",
    "jobs.lever.co",
    "jobs.eu.lever.co",
    "jobs.ashbyhq.com",
]


@dataclass(frozen=True)
class BoardRef:
    ats: Ats
    slug: str
    job_id: str | None
    eu: bool = False


@dataclass
class BoardJob:
    ats: Ats
    slug: str
    external_id: str
    url: str
    title: str
    company: str
    location_text: str
    country_code: str | None
    remote: bool
    workplace_type: str | None  # onsite | hybrid | remote
    posted_at: date | None
    apply_url: str
    text: str
    own_domain: str | None = None
    needs_text: bool = False  # Greenhouse light list: call BoardsService.fill_text()


def _clean_url(url: str) -> str:
    return re.split(r"[?#&]", url.strip(), maxsplit=1)[0].rstrip("/")


def detect(url: str) -> BoardRef | None:
    """Parse a job or board URL. Returns None for anything we can't verify via an API."""
    raw = url.strip()
    p = urlparse(_clean_url(raw))
    host = p.netloc.lower().removeprefix("www.")
    parts = [x for x in p.path.split("/") if x]
    if "greenhouse.io" in host:
        if parts and parts[0] == "embed":
            q = parse_qs(urlparse(raw).query)
            slug = q.get("for", [""])[0]
            token = q.get("token", [""])[0] or None
            return BoardRef("greenhouse", slug, token) if slug else None
        if not parts:
            return None
        job_id = parts[2] if len(parts) >= 3 and parts[1] == "jobs" and parts[2].isdigit() else None
        return BoardRef("greenhouse", parts[0], job_id)
    if host in ("jobs.lever.co", "jobs.eu.lever.co") and parts:
        return BoardRef(
            "lever", parts[0], parts[1] if len(parts) >= 2 else None, eu=host.startswith("jobs.eu.")
        )
    if host == "jobs.ashbyhq.com" and parts:
        return BoardRef("ashby", parts[0], parts[1] if len(parts) >= 2 else None)
    return None


def _date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value / 1000, tz=UTC).date()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _title_case(slug: str) -> str:
    return re.sub(r"[-_]+", " ", slug).strip().title()


def _workplace(value: str | None, remote: bool) -> str | None:
    """The board's explicit value wins; the remote flag only fills a missing value."""
    v = (value or "").lower().replace("-", "").replace("_", "").replace(" ", "")
    if v == "remote":
        return "remote"
    if v == "hybrid":
        return "hybrid"
    if v == "onsite":
        return "onsite"
    if remote:
        return "remote"
    return None


def parse_greenhouse(slug: str, data: dict[str, Any]) -> list[BoardJob]:
    jobs = []
    for j in data.get("jobs", []):
        loc = (j.get("location") or {}).get("name") or ""
        absolute = j.get("absolute_url") or ""
        host = urlparse(absolute).netloc.lower()
        own = host.removeprefix("www.") if host and "greenhouse.io" not in host else None
        jid = str(j.get("id"))
        jobs.append(
            BoardJob(
                ats="greenhouse",
                slug=slug,
                external_id=jid,
                url=f"https://job-boards.greenhouse.io/{slug}/jobs/{jid}",
                title=(j.get("title") or "").strip(),
                company=(j.get("company_name") or _title_case(slug)).strip(),
                location_text=loc,
                country_code=None,
                remote="remote" in loc.lower(),
                workplace_type=_workplace(None, "remote" in loc.lower()),
                posted_at=_date(j.get("first_published")) or _date(j.get("updated_at")),
                apply_url=absolute or f"https://job-boards.greenhouse.io/{slug}/jobs/{jid}",
                # The light list has no content: text is fetched per job only for candidates.
                text=html_to_text(j.get("content") or "", escaped=True) if j.get("content") else "",
                own_domain=own,
                needs_text=not j.get("content"),
            )
        )
    return jobs


def parse_lever(slug: str, data: list[dict[str, Any]]) -> list[BoardJob]:
    jobs = []
    for j in data:
        cats = j.get("categories") or {}
        locs = [cats.get("location") or "", *(cats.get("allLocations") or [])]
        loc = ", ".join(dict.fromkeys(x for x in locs if x))
        wt = j.get("workplaceType")
        remote = (wt or "").lower() == "remote" or "remote" in loc.lower()
        parts = [j.get("descriptionPlain") or ""]
        for lst in j.get("lists") or []:
            parts.append(lst.get("text") or "")
            parts.append(html_to_text(lst.get("content") or ""))
        parts.append(j.get("additionalPlain") or "")
        jobs.append(
            BoardJob(
                ats="lever",
                slug=slug,
                external_id=str(j.get("id")),
                url=_clean_url(j.get("hostedUrl") or ""),
                title=(j.get("text") or "").strip(),
                company=_title_case(slug),
                location_text=loc,
                country_code=(j.get("country") or None),
                remote=remote,
                workplace_type=_workplace(wt, remote),
                posted_at=_date(j.get("createdAt")),
                apply_url=j.get("applyUrl") or j.get("hostedUrl") or "",
                text="\n".join(p.strip() for p in parts if p and p.strip()),
            )
        )
    return jobs


def parse_ashby(slug: str, data: dict[str, Any]) -> list[BoardJob]:
    jobs = []
    for j in data.get("jobs", []):
        locs = [j.get("location") or ""]
        locs += [s.get("location") or "" for s in j.get("secondaryLocations") or []]
        addr = (j.get("address") or {}).get("postalAddress") or {}
        locs += [addr.get("addressLocality") or "", addr.get("addressCountry") or ""]
        loc = ", ".join(dict.fromkeys(x for x in locs if x))
        remote = bool(j.get("isRemote")) or (j.get("workplaceType") or "").lower() == "remote"
        job_url = _clean_url(j.get("jobUrl") or "")
        jobs.append(
            BoardJob(
                ats="ashby",
                slug=slug,
                external_id=job_url.rsplit("/", 1)[-1] or str(j.get("id")),
                url=job_url,
                title=(j.get("title") or "").strip(),
                company=_title_case(slug),
                location_text=loc,
                country_code=None,
                remote=remote,
                workplace_type=_workplace(j.get("workplaceType"), remote),
                posted_at=_date(j.get("publishedAt")),
                apply_url=j.get("applyUrl") or job_url,
                text=(j.get("descriptionPlain") or "").strip(),
            )
        )
    return jobs


MAX_BOARD_BYTES = 6 * 1024 * 1024  # job aggregators can return 40+ MB; skip those boards
BOARD_DEADLINE_SECONDS = 20


class BoardTooLargeError(ValueError):
    pass


class BoardsService:
    """Fetches a company's open jobs. Lists are cached for 6 h (free API, but be polite)."""

    _cache: dict[tuple[str, str, bool], tuple[float, list[BoardJob]]] = {}
    _texts: dict[str, str] = {}

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=15, follow_redirects=True, headers={"User-Agent": USER_AGENT}
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def jobs(self, ref: BoardRef) -> list[BoardJob] | None:
        """All open jobs on the board, or None if the board can't be read."""
        key = (ref.ats, ref.slug.lower(), ref.eu)
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < BOARD_CACHE_SECONDS:
            return hit[1]
        try:
            jobs = await asyncio.wait_for(self._fetch(ref), BOARD_DEADLINE_SECONDS)
        except (httpx.HTTPError, ValueError, TimeoutError) as e:
            log.warning("Board %s/%s skipped: %s", ref.ats, ref.slug, e or type(e).__name__)
            return None
        if jobs is not None:
            self._cache[key] = (time.monotonic(), jobs)
        return jobs

    async def fill_text(self, job: BoardJob) -> None:
        """Fetch the full text of one Greenhouse job (the light list has none)."""
        if not job.needs_text:
            return
        if job.url in self._texts:
            job.text, job.needs_text = self._texts[job.url], False
            return
        api = f"https://boards-api.greenhouse.io/v1/boards/{job.slug}/jobs/{job.external_id}"
        try:
            r = await self._client.get(api)
            if r.status_code == 200:
                content = r.json().get("content") or ""
                job.text = await asyncio.to_thread(html_to_text, content, escaped=True)
                self._texts[job.url] = job.text
        except (httpx.HTTPError, ValueError) as e:
            log.warning("Job text %s failed: %s", job.url, e)
        job.needs_text = False

    async def _get_json(self, url: str) -> Any | None:
        async with self._client.stream("GET", url) as r:
            if r.status_code == 404:
                return None
            r.raise_for_status()
            size = int(r.headers.get("content-length") or 0)
            if size > MAX_BOARD_BYTES:
                raise BoardTooLargeError(f"board too large ({size} bytes)")
            chunks, total = [], 0
            async for chunk in r.aiter_bytes():
                total += len(chunk)
                if total > MAX_BOARD_BYTES:
                    raise BoardTooLargeError("board too large")
                chunks.append(chunk)
        return json.loads(b"".join(chunks))

    async def _fetch(self, ref: BoardRef) -> list[BoardJob] | None:
        if ref.ats == "greenhouse":
            url = f"https://boards-api.greenhouse.io/v1/boards/{ref.slug}/jobs"
        elif ref.ats == "lever":
            base = "https://api.eu.lever.co" if ref.eu else "https://api.lever.co"
            url = f"{base}/v0/postings/{ref.slug}?mode=json"
        else:
            url = f"https://api.ashbyhq.com/posting-api/job-board/{ref.slug}"
        data = await self._get_json(url)
        if data is None:
            return None
        # Parsing large boards is CPU work: keep it off the event loop.
        if ref.ats == "greenhouse":
            return await asyncio.to_thread(parse_greenhouse, ref.slug, data)
        if ref.ats == "lever":
            return await asyncio.to_thread(
                parse_lever, ref.slug, data if isinstance(data, list) else []
            )
        return await asyncio.to_thread(parse_ashby, ref.slug, data)
