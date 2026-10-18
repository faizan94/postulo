"""Places (D9, D22): search the list, accept typed places, match job locations, widen in country.

Kinds: city, country, region (Europe, DACH), remote. A typed place we don't know becomes a city
with no country and is matched by name. No places at all means "Anywhere" (no filter).
"""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.domain.normalize import fold, spelling_variants
from app.schemas.common import Place

_DATA = Path(__file__).parent / "data" / "places.json"
REMOTE = Place(kind="remote", name="Remote", country_code=None)
POPULAR = ["Berlin", "Munich", "Hamburg", "Germany", "Remote", "Europe", "Amsterdam", "London"]


@dataclass(frozen=True)
class JobLocation:
    """What we know about where a job is."""

    text: str  # free text from the board, e.g. "Berlin, Germany" or "Remote - EU"
    country_code: str | None = None
    remote: bool = False


def _word(alias: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w]){re.escape(alias)}(?![\w])", re.IGNORECASE)


def _variants(names: list[str]) -> list[str]:
    """Every spelling of each name: 'München' -> münchen, munchen, muenchen (tokenized form)."""
    out: list[str] = []
    for n in names:
        for v in sorted(spelling_variants(n)):
            if v not in out:
                out.append(v)
    return out


def _pats(names: list[str], min_len: int = 0) -> list[re.Pattern[str]]:
    return [_word(v) for v in _variants(names) if len(v) > min_len]


class Places:
    def __init__(self, data: dict[str, Any]) -> None:
        self.countries: dict[str, dict[str, Any]] = {c["code"]: c for c in data["countries"]}
        self.cities: list[dict[str, Any]] = data["cities"]
        self.regions: dict[str, dict[str, Any]] = {r["name"]: r for r in data.get("regions", [])}
        self._country_pats = {
            code: _pats([c["name"], *c["aliases"]], min_len=2) for code, c in self.countries.items()
        }
        self._city_pats = [(c, _pats([c["name"], *c["aliases"]])) for c in self.cities]
        self._region_pats = {name: _pats([name, *r["aliases"]]) for name, r in self.regions.items()}

    def all_places(self) -> list[Place]:
        out = [REMOTE]
        out += [Place(kind="region", name=name) for name in self.regions]
        out += [
            Place(kind="country", name=c["name"], country_code=code)
            for code, c in self.countries.items()
        ]
        out += [Place(kind="city", name=c["name"], country_code=c["country"]) for c in self.cities]
        return out

    def _aliases(self, p: Place) -> list[str]:
        """Folded spellings of a place, for typed search and resolve."""
        if p.kind == "remote":
            names = ["remote", "anywhere remote"]
        elif p.kind == "region":
            names = [p.name, *self.regions[p.name]["aliases"]]
        elif p.kind == "country":
            names = [p.name, *self.countries[p.country_code or ""]["aliases"]]
        else:
            city = next(c for c in self.cities if c["name"] == p.name)
            names = [p.name, *city["aliases"]]
        return [fold(v) for v in _variants(names)]

    def search(self, q: str, limit: int = 10) -> list[Place]:
        q = fold(q)
        places = self.all_places()
        if not q:
            by_name = {p.name: p for p in places}
            return [by_name[n] for n in POPULAR if n in by_name]
        starts = [p for p in places if any(a.startswith(q) for a in self._aliases(p))]
        contains = [p for p in places if p not in starts and any(q in a for a in self._aliases(p))]
        return (starts + contains)[:limit]

    def resolve(self, name: str) -> Place:
        """A typed place -> the known place with that exact name/alias, else a custom city."""
        q = fold(name)
        for p in self.all_places():
            if q in self._aliases(p):
                return p
        return Place(kind="city", name=" ".join(name.split())[:80], country_code=None)

    def tavily_country(self, place: Place) -> str | None:
        if place.country_code and place.country_code in self.countries:
            return str(self.countries[place.country_code]["tavily"])
        return None

    def country_place(self, code: str) -> Place | None:
        c = self.countries.get(code)
        return Place(kind="country", name=c["name"], country_code=code) if c else None

    def widen(self, place: Place) -> Place | None:
        """City -> its country. Countries, regions and Remote don't widen (D9)."""
        if place.kind == "city" and place.country_code:
            return self.country_place(place.country_code)
        return None

    def _in_country(self, job: JobLocation, code: str) -> bool:
        if job.country_code and job.country_code.upper() == code:
            return True
        if any(p.search(job.text) for p in self._country_pats.get(code, [])):
            return True
        return any(
            any(p.search(job.text) for p in pats)
            for c, pats in self._city_pats
            if c["country"] == code
        )

    def matches(self, job: JobLocation, place: Place) -> bool:
        if place.kind == "remote":
            return job.remote
        if place.kind == "region":
            region = self.regions.get(place.name)
            if region is None:
                return _word(place.name).search(job.text) is not None
            if any(self._in_country(job, code) for code in region["countries"]):
                return True
            return job.remote and any(p.search(job.text) for p in self._region_pats[place.name])
        if place.kind == "city":
            pats = next((p for c, p in self._city_pats if c["name"] == place.name), None)
            in_city = (
                any(p.search(job.text) for p in pats)
                if pats is not None
                else _word(place.name).search(job.text) is not None
            )
            # D22: a remote job in the city's country also works for someone living there.
            return in_city or bool(
                job.remote and place.country_code and self._in_country(job, place.country_code)
            )
        return self._in_country(job, place.country_code or "")

    def matches_any(self, job: JobLocation, wanted: list[Place]) -> bool:
        """No places = Anywhere (D22)."""
        return not wanted or any(self.matches(job, p) for p in wanted)

    def place_of(self, job: JobLocation) -> Place | None:
        """Best structured place for a job: a known city, else its country, else Remote."""
        for c, pats in self._city_pats:
            if any(p.search(job.text) for p in pats):
                return Place(kind="city", name=c["name"], country_code=c["country"])
        for code in self.countries:
            if self._in_country(job, code):
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

    def find_all(self, text: str) -> list[Place]:
        """Every known place mentioned in a free-text search, in order (D21)."""
        found: list[tuple[int, Place]] = []
        if re.search(r"\bremote\b|\bhome ?office\b|\bfully remote\b", text, re.I):
            m = re.search(r"\bremote\b|\bhome ?office\b", text, re.I)
            found.append((m.start() if m else 0, REMOTE))
        for name, pats in self._region_pats.items():
            for p in pats:
                if (m := p.search(text)) and len(m.group(0)) > 2:
                    found.append((m.start(), Place(kind="region", name=name)))
                    break
        for code, pats in self._country_pats.items():
            for p in pats:
                if m := p.search(text):
                    found.append((m.start(), self.country_place(code)))  # type: ignore[arg-type]
                    break
        for c, pats in self._city_pats:
            for p in pats:
                if m := p.search(text):
                    found.append(
                        (m.start(), Place(kind="city", name=c["name"], country_code=c["country"]))
                    )
                    break
        out: list[Place] = []
        for _, place in sorted(found, key=lambda x: x[0]):
            if place not in out:
                out.append(place)
        return out


@lru_cache
def places() -> Places:
    return Places(json.loads(_DATA.read_text(encoding="utf-8")))
