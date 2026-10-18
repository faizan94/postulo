"""Skill, soft-skill, language and job-title glossary (D2). Data: data/glossary.json."""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

TermKind = Literal["skill", "soft", "language"]

_DATA = Path(__file__).parent / "data" / "glossary.json"


@dataclass(frozen=True)
class Term:
    name: str
    kind: TermKind
    type: str  # tech | domain | soft | language
    ci: re.Pattern[str] | None  # case-insensitive aliases, no context needed
    cs: re.Pattern[str] | None  # case-sensitive aliases, need a context word on the line
    context: tuple[str, ...]


@dataclass(frozen=True)
class Hit:
    term: Term
    start: int
    end: int


def _ci_pattern(aliases: list[str]) -> re.Pattern[str] | None:
    if not aliases:
        return None
    alt = "|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True))
    return re.compile(rf"(?<![\w])(?:{alt})(?![\w])", re.IGNORECASE)


def _cs_pattern(aliases: list[str]) -> re.Pattern[str] | None:
    if not aliases:
        return None
    alt = "|".join(re.escape(a) for a in aliases)
    return re.compile(rf"(?<![\w\-])(?:{alt})(?![\w\-&])")


class Glossary:
    def __init__(self, data: dict[str, object]) -> None:
        self.terms: list[Term] = []
        self._canon: dict[str, str] = {}
        for kind, key in (("skill", "skills"), ("soft", "soft"), ("language", "languages")):
            for entry in data[key]:  # type: ignore[attr-defined]
                name = entry["name"]
                # Ambiguous short names ("Go", "R", "CV") match only via cs_aliases + context.
                own = [] if entry.get("cs_aliases") else [name.lower()]
                aliases = [*own, *entry.get("aliases", [])]
                term_type = entry.get("type", "soft" if kind == "soft" else "language")
                self.terms.append(
                    Term(
                        name=name,
                        kind=kind,  # type: ignore[arg-type]
                        type=term_type,
                        ci=_ci_pattern(aliases),
                        cs=_cs_pattern(entry.get("cs_aliases", [])),
                        context=tuple(c.lower() for c in entry.get("context", [])),
                    )
                )
                for a in [name.lower(), *aliases, *entry.get("cs_aliases", [])]:
                    self._canon[a.lower()] = name
        self._related: dict[str, set[str]] = {}
        for group in data["related"]:  # type: ignore[attr-defined]
            for name in group:
                self._related.setdefault(name, set()).update(n for n in group if n != name)
        self.titles: list[str] = [t["name"] for t in data["titles"]]  # type: ignore[attr-defined]
        self._title_related: dict[str, list[str]] = {
            t["name"]: list(t.get("related", []))
            for t in data["titles"]  # type: ignore[attr-defined]
        }
        self._title_patterns = [
            (t, re.compile(rf"(?<![\w]){re.escape(t)}(?![\w])", re.IGNORECASE)) for t in self.titles
        ]

    def find(self, line: str) -> list[Hit]:
        """All glossary terms on one line (first hit per term)."""
        hits: list[Hit] = []
        lower = line.lower()
        for term in self.terms:
            m = term.ci.search(line) if term.ci else None
            if m is None and term.cs is not None:
                cm = term.cs.search(line)
                if cm and any(c in lower for c in term.context):
                    m = cm
            if m is not None:
                hits.append(Hit(term, m.start(), m.end()))
        return hits

    def canonical(self, name: str) -> str:
        """Canonical name for a known alias, else the input with tidy spacing."""
        key = " ".join(name.split()).lower()
        return self._canon.get(key, " ".join(name.split()))

    def is_related(self, a: str, b: str) -> bool:
        return b in self._related.get(a, set())

    def related_to(self, name: str) -> set[str]:
        return set(self._related.get(name, set()))

    def find_titles(self, text: str) -> list[str]:
        """Known job titles in order of first appearance."""
        found: list[tuple[int, str]] = []
        for title, pat in self._title_patterns:
            m = pat.search(text)
            if m:
                found.append((m.start(), title))
        return [t for _, t in sorted(found)]

    def related_titles(self, title: str) -> list[str]:
        for known, related in self._title_related.items():
            if known.lower() == title.lower():
                return related
        return []


@lru_cache
def glossary() -> Glossary:
    return Glossary(json.loads(_DATA.read_text(encoding="utf-8")))
