"""Tavily wrapper: job search on ATS/career sites, page extraction, company lookups."""

import logging
from typing import Any, Literal, Self

from tavily import AsyncTavilyClient
from tavily import errors as tavily_errors

from app.config import Settings
from app.errors import MissingAPIKeyError, UpstreamError

log = logging.getLogger(__name__)

# Applicant-tracking systems and job boards where companies post first (idea.md section 7).
ATS_DOMAINS: list[str] = [
    "boards.greenhouse.io",
    "job-boards.greenhouse.io",
    "jobs.lever.co",
    "jobs.ashbyhq.com",
    "jobs.personio.de",
    "jobs.personio.com",
    "myworkdayjobs.com",
    "join.com",
    "jobs.smartrecruiters.com",
    "apply.workable.com",
    "recruitee.com",
]

TimeRange = Literal["day", "week", "month", "year"]


class TavilyService:
    def __init__(self, settings: Settings) -> None:
        if not settings.tavily_api_key:
            raise MissingAPIKeyError("TAVILY_API_KEY")
        self._client = AsyncTavilyClient(api_key=settings.tavily_api_key)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._client.close()

    async def search(
        self,
        query: str,
        *,
        include_domains: list[str] | None = None,
        time_range: TimeRange | None = None,
        max_results: int = 10,
        search_depth: Literal["basic", "advanced", "fast", "ultra-fast"] = "basic",
    ) -> list[dict[str, Any]]:
        """Return Tavily results: [{title, url, content, score, published_date?}, ...]."""
        try:
            res = await self._client.search(
                query,
                # Set explicitly: auto_parameters can silently switch to 2-credit "advanced".
                search_depth=search_depth,
                include_domains=include_domains,
                time_range=time_range,
                max_results=max_results,
            )
        except Exception as e:  # tavily raises several unrelated types
            raise _wrap(e) from e
        results: list[dict[str, Any]] = res.get("results", [])
        return results

    async def search_jobs(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        return await self.search(
            query, include_domains=ATS_DOMAINS, time_range="month", max_results=max_results
        )

    async def extract(self, urls: list[str]) -> dict[str, str]:
        """Return {url: page text} for the URLs Tavily could read (max 20 per call)."""
        out: dict[str, str] = {}
        for i in range(0, len(urls), 20):
            try:
                res = await self._client.extract(urls[i : i + 20], format="markdown")
            except Exception as e:
                log.warning("Tavily extract failed: %s", e)
                continue
            for item in res.get("results", []):
                if item.get("url") and item.get("raw_content"):
                    out[item["url"]] = item["raw_content"]
        return out


def _wrap(e: Exception) -> UpstreamError:
    if isinstance(e, tavily_errors.InvalidAPIKeyError):
        return UpstreamError("Tavily rejected TAVILY_API_KEY. Check the key.")
    if isinstance(e, tavily_errors.UsageLimitExceededError):
        return UpstreamError("Tavily usage limit exceeded.")
    return UpstreamError(f"Tavily error: {e}")
