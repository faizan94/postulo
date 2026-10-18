"""Skill, soft-skill, language and job-title glossary (D2). Data: data/glossary.json."""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from app.domain.normalize import key as norm_key

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


_SEP = re.compile(r"(?<=\w)[\s.\-/]+(?=\w)")


def _flexible(alias: str) -> str:
    """Regex for an alias where inner separators are optional: 'node.js' also finds 'Node JS',
    'NodeJS'; 'power bi' finds 'PowerBI'; 'scikit-learn' finds 'scikit learn'."""
    parts = _SEP.split(alias)
    return r"[\s.\-/]?".join(re.escape(p) for p in parts)


def _ci_pattern(aliases: list[str]) -> re.Pattern[str] | None:
    if not aliases:
        return None
    alt = "|".join(_flexible(a) for a in sorted(aliases, key=len, reverse=True))
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
                for a in [name, *aliases, *entry.get("cs_aliases", [])]:
                    self._canon.setdefault(norm_key(a), name)
        self._by_name: dict[str, Term] = {t.name: t for t in self.terms}
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
        """All glossary terms on one line, one hit per term.

        Longest match wins: inside "React Native" there is no separate "React", and
        "Apache Spark" is not also "Spark". A later standalone mention still counts.
        """
        lower = line.lower()
        spans: list[Hit] = []
        for term in self.terms:
            found = list(term.ci.finditer(line)) if term.ci else []
            if not found and term.cs is not None and any(c in lower for c in term.context):
                found = list(term.cs.finditer(line))
            spans += [Hit(term, m.start(), m.end()) for m in found]

        def inside_longer(h: Hit) -> bool:
            return any(
                o.start <= h.start and h.end <= o.end and (o.end - o.start) > (h.end - h.start)
                for o in spans
            )

        hits: list[Hit] = []
        seen: set[str] = set()
        for h in sorted(spans, key=lambda x: x.start):
            if h.term.name not in seen and not inside_longer(h):
                seen.add(h.term.name)
                hits.append(h)
        return hits

    def canonical(self, name: str) -> str:
        """Canonical name for a known alias (any case/spelling), else the input, tidied."""
        return self._canon.get(norm_key(name), " ".join(name.split()))

    def term(self, name: str) -> Term | None:
        """The glossary entry for any spelling of a name ('REACT', 'react.js' -> React)."""
        return self._by_name.get(self.canonical(name))

    def is_known(self, name: str) -> bool:
        return norm_key(name) in self._canon

    def key_of(self, name: str) -> str:
        """The comparison key of a skill: same key = same skill (D2, tokenized form)."""
        return norm_key(self.canonical(name))

    def is_related(self, a: str, b: str) -> bool:
        return self.canonical(b) in self._related.get(self.canonical(a), set())

    def related_to(self, name: str) -> set[str]:
        return set(self._related.get(self.canonical(name), set()))

    def find_titles(self, text: str) -> list[str]:
        """Known job titles in order of first appearance."""
        found: list[tuple[int, str]] = []
        for title, pat in self._title_patterns:
            m = pat.search(text)
            if m:
                found.append((m.start(), title))
        return [t for _, t in sorted(found)]

    def related_titles(self, title: str) -> list[str]:
        """Related titles for this role. Seniority words are ignored, so
        'Senior Software Engineer' uses the 'Software Engineer' entry."""
        from app.domain.titles import SENIORITY

        candidates = [title]
        stripped = " ".join(w for w in title.split() if w.lower() not in SENIORITY)
        if stripped and stripped.lower() != title.lower():
            candidates.append(stripped)
        for candidate in candidates:
            for known, related in self._title_related.items():
                if known.lower() == candidate.lower():
                    return related
        return []


@lru_cache
def glossary() -> Glossary:
    return Glossary(json.loads(_DATA.read_text(encoding="utf-8")))
