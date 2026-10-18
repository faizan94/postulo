"""Search agent: turns profile + preferences into Tavily queries over ATS/career sites."""

import asyncio
import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.models.schemas import Preferences, Profile
from app.services.tavily_client import TavilyService

log = logging.getLogger(__name__)

LOCATION_TERMS = {"Berlin": "Berlin", "Germany": "Germany", "World": "remote"}


@dataclass
class RawPosting:
    """A search hit before verification/scoring."""

    title: str
    company: str | None
    url: str
    snippet: str
    published_date: str | None
    source: str


def build_queries(profile: Profile, prefs: Preferences, max_queries: int = 3) -> list[str]:
    location = LOCATION_TERMS[prefs.location]
    roles = profile.target_roles or ([profile.headline] if profile.headline else [])
    roles = [r for r in roles if r][:2] or ["software engineer"]
    top_skills = " ".join(profile.skills[:3])
    queries = [f'"{role}" job {location}' for role in roles]
    if top_skills:
        queries.append(f"{roles[0]} {top_skills} {location} job opening")
    if prefs.prompt.strip():
        queries.append(f"{roles[0]} {prefs.prompt.strip()[:120]} {location}")
    return queries[:max_queries]


def company_from_url(url: str) -> str | None:
    """Guess the company from well-known ATS URL layouts."""
    p = urlparse(url)
    host, parts = p.netloc.lower(), [x for x in p.path.split("/") if x]
    slug: str | None = None
    if "greenhouse.io" in host or "lever.co" in host or "ashbyhq.com" in host:
        slug = parts[0] if parts else None
    elif "personio." in host or "recruitee.com" in host or "myworkdayjobs.com" in host:
        slug = host.split(".")[0]
    elif host.endswith("join.com") and len(parts) >= 2 and parts[0] == "companies":
        slug = parts[1]
    elif "smartrecruiters.com" in host or "workable.com" in host:
        slug = parts[0] if parts else None
    if not slug or slug in {"embed", "jobs", "www", "apply"}:
        return None
    return re.sub(r"[-_]+", " ", slug).strip().title()


def title_from_result(raw_title: str, company: str | None) -> str:
    t = raw_title.strip()
    m = re.match(r"Job Application for (.+?) at (.+)", t, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    for sep in (" | ", " - ", " – ", " @ "):
        if sep in t:
            t = t.split(sep)[0].strip()
    if company and t.lower().endswith(f" at {company.lower()}"):
        t = t[: -len(company) - 4]
    return t or raw_title


def looks_like_posting(url: str) -> bool:
    """Skip board index pages; keep URLs that point at a single job."""
    path = [x for x in urlparse(url).path.split("/") if x]
    return len(path) >= 2 or any(ch.isdigit() for ch in url.rsplit("/", 1)[-1])


async def search_postings(
    profile: Profile,
    prefs: Preferences,
    tavily: TavilyService,
    limit: int = 20,
    exclude: set[str] | None = None,
) -> list[RawPosting]:
    """Run the queries in parallel and dedupe. `exclude` skips URLs seen in earlier rounds."""
    queries = build_queries(profile, prefs)
    log.info("Search queries: %s", queries)
    batches = await asyncio.gather(*(tavily.search_jobs(q, max_results=10) for q in queries))
    seen: set[str] = set(exclude or ())
    postings: list[RawPosting] = []
    for results in batches:
        for r in results:
            url = (r.get("url") or "").split("?")[0]
            if not url or url in seen or not looks_like_posting(url):
                continue
            seen.add(url)
            company = company_from_url(url)
            postings.append(
                RawPosting(
                    title=title_from_result(r.get("title") or "Untitled role", company),
                    company=company,
                    url=url,
                    snippet=r.get("content") or "",
                    published_date=r.get("published_date"),
                    source=urlparse(url).netloc,
                )
            )
    return postings[:limit]
