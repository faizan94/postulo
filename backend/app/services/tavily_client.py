"""Tavily search over the raw HTTP API.

The raw API is used (not the SDK) because the installed SDK has no `include_published_date`
argument; the API accepts it (checked live on 18 Oct 2026). Results are cached in memory for
6 h, so repeated searches cost no credits.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Literal, Self

import httpx

from app.config import Settings
from app.errors import MissingAPIKeyError, UpstreamError

log = logging.getLogger(__name__)

SEARCH_URL = "https://api.tavily.com/search"
CACHE_SECONDS = 6 * 3600
TimeRange = Literal["day", "week", "month", "year"]


@dataclass
class SearchResult:
    results: list[dict[str, Any]]
    credits: int  # 0 when served from cache


class TavilyService:
    _cache: dict[tuple[Any, ...], tuple[float, list[dict[str, Any]]]] = {}

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        if not settings.tavily_api_key:
            raise MissingAPIKeyError("TAVILY_API_KEY")
        self._key = settings.tavily_api_key
        self._client = client or httpx.AsyncClient(timeout=40)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._client.aclose()

    async def search(
        self,
        query: str,
        *,
        include_domains: list[str] | None = None,
        time_range: TimeRange | None = "month",
        max_results: int = 10,
        country: str | None = None,
    ) -> SearchResult:
        key = (query, tuple(include_domains or ()), time_range, max_results, country)
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
            return SearchResult(results=hit[1], credits=0)
        body: dict[str, Any] = {
            "query": query,
            # Set explicitly: auto_parameters can silently switch to 2-credit "advanced".
            "search_depth": "basic",
            "max_results": max_results,
            "include_published_date": True,
            "include_usage": True,
            "topic": "general",
        }
        if include_domains:
            body["include_domains"] = include_domains
        if time_range:
            body["time_range"] = time_range
        if country:
            body["country"] = country  # a boost, not a filter; general topic only
        try:
            r = await self._client.post(
                SEARCH_URL, json=body, headers={"Authorization": f"Bearer {self._key}"}
            )
        except httpx.HTTPError as e:
            raise UpstreamError(f"Tavily is unreachable: {type(e).__name__}") from e
        if r.status_code == 401:
            raise UpstreamError("Tavily rejected TAVILY_API_KEY. Check the key.")
        if r.status_code in (429, 432, 433):
            raise UpstreamError("Tavily usage or rate limit reached.")
        if r.status_code >= 400:
            raise UpstreamError(f"Tavily error (HTTP {r.status_code}).")
        data = r.json()
        results = list(data.get("results", []))
        credits = int((data.get("usage") or {}).get("credits", 1))
        self._cache[key] = (time.monotonic(), results)
        return SearchResult(results=results, credits=credits)
