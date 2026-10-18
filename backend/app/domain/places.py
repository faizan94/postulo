"""Structured places (D9): search the fixed list, match job locations, widen in country."""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.schemas.common import Place

_DATA = Path(__file__).parent / "data" / "places.json"
REMOTE = Place(kind="remote", name="Remote", country_code=None)
POPULAR = ["Berlin", "Munich", "Hamburg", "Germany", "Remote", "Amsterdam", "London", "Vienna"]


@dataclass(frozen=True)
class JobLocation:
    """What we know about where a job is."""

    text: str  # free text from the board, e.g. "Berlin, Germany" or "Remote - EU"
    country_code: str | None = None
    remote: bool = False


def _word(alias: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w]){re.escape(alias)}(?![\w])", re.IGNORECASE)


class Places:
    def __init__(self, data: dict[str, Any]) -> None:
        self.countries: dict[str, dict[str, Any]] = {c["code"]: c for c in data["countries"]}
        self.cities: list[dict[str, Any]] = data["cities"]
        self._country_pats = {
            code: [_word(a) for a in c["aliases"] if len(a) > 2]
            for code, c in self.countries.items()
        }
        self._city_pats = [(c, [_word(a) for a in c["aliases"]]) for c in self.cities]

    def all_places(self) -> list[Place]:
        out = [REMOTE]
        out += [
            Place(kind="country", name=c["name"], country_code=code)
            for code, c in self.countries.items()
        ]
        out += [Place(kind="city", name=c["name"], country_code=c["country"]) for c in self.cities]
        return out

    def search(self, q: str, limit: int = 10) -> list[Place]:
        q = q.strip().casefold()
        places = self.all_places()
        if not q:
            by_name = {p.name: p for p in places}
            return [by_name[n] for n in POPULAR if n in by_name]

        def aliases(p: Place) -> list[str]:
            if p.kind == "remote":
                return ["remote"]
            if p.kind == "country":
                return [p.name.casefold(), *self.countries[p.country_code or ""]["aliases"]]
            city = next(c for c in self.cities if c["name"] == p.name)
            return [p.name.casefold(), *city["aliases"]]

        starts = [p for p in places if any(a.startswith(q) for a in aliases(p))]
        contains = [p for p in places if p not in starts and any(q in a for a in aliases(p))]
        return (starts + contains)[:limit]

    def tavily_country(self, place: Place) -> str | None:
        if place.country_code and place.country_code in self.countries:
            return str(self.countries[place.country_code]["tavily"])
        return None

    def country_place(self, code: str) -> Place | None:
        c = self.countries.get(code)
        return Place(kind="country", name=c["name"], country_code=code) if c else None

    def widen(self, place: Place) -> Place | None:
        """City -> its country. Countries and Remote don't widen (D9)."""
        if place.kind == "city" and place.country_code:
            return self.country_place(place.country_code)
        return None

    def matches(self, job: JobLocation, place: Place) -> bool:
        if place.kind == "remote":
            return job.remote
        if place.kind == "city":
            city = next((c for c, _ in self._city_pats if c["name"] == place.name), None)
            pats = next((p for c, p in self._city_pats if c["name"] == place.name), [])
            if city is None:
                return _word(place.name).search(job.text) is not None
            return any(p.search(job.text) for p in pats)
        code = place.country_code or ""
        if job.country_code and job.country_code.upper() == code:
            return True
        if any(p.search(job.text) for p in self._country_pats.get(code, [])):
            return True
        return any(
            any(p.search(job.text) for p in pats)
            for c, pats in self._city_pats
            if c["country"] == code
        )

    def place_of(self, job: JobLocation) -> Place | None:
        """Best structured place for a job: a known city, else its country, else Remote."""
        for c, pats in self._city_pats:
            if any(p.search(job.text) for p in pats):
                return Place(kind="city", name=c["name"], country_code=c["country"])
        for code in self.countries:
            if self.matches(
                job, Place(kind="country", name=self.countries[code]["name"], country_code=code)
            ):
                return self.country_place(code)
        return REMOTE if job.remote else None

    def find_city(self, text: str) -> Place | None:
        """The first known city mentioned in a text (used to suggest a place from a CV)."""
        best: tuple[int, dict[str, Any]] | None = None
        for c, pats in self._city_pats:
            for p in pats:
                m = p.search(text)
                if m and (best is None or m.start() < best[0]):
                    best = (m.start(), c)
        if best is None:
            return None
        return Place(kind="city", name=best[1]["name"], country_code=best[1]["country"])


@lru_cache
def places() -> Places:
    return Places(json.loads(_DATA.read_text(encoding="utf-8")))
