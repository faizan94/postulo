"""Postings -> requirements with verified quotes. LLM in batches of 5, rules as fallback.

Cached on the posting by text hash: the same posting text is never extracted twice.
"""

import hashlib
import re
from typing import Any

from pydantic import ValidationError

from app.agents.llm_gate import LLMGate
from app.agents.prompts.requirements import REQUIREMENTS_SYSTEM_PROMPT
from app.db.tables import Posting
from app.domain.evidence import EvidenceChecker
from app.domain.glossary import glossary
from app.domain.rules import extract_requirements
from app.schemas.common import Evidence
from app.schemas.posting import Requirement

EXTRACTION_VERSION = "v4"  # bump when extraction logic changes: old cache entries re-run
RULES_MODEL = f"rules@{EXTRACTION_VERSION}"
BATCH = 5
MAX_TEXT_PER_POSTING = 8_000
TYPES = {"tech", "soft", "domain", "language", "years", "degree"}


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


_PAREN = re.compile(r"\([^)]*\)")
_AND = re.compile(r"\s*(?:,|;|&|\band\b|\bund\b|\s\+\s)\s*", re.I)
_ALT = re.compile(r"\s*(?:/|\||\bor\b|\boder\b)\s*", re.I)


def _known(part: str) -> tuple[str, str] | None:
    """(canonical name, type) if the glossary knows this part, in any spelling."""
    g = glossary()
    term = g.term(part)
    if term is None:
        # a glossary term that covers (almost) the whole part, e.g. "Apache Spark 3"
        hits = [h for h in g.find(part) if (h.end - h.start) >= 0.7 * len(part.strip())]
        term = hits[0].term if hits else None
    if term is None:
        return None
    return term.name, "soft" if term.kind == "soft" else term.type


def canonical_names(name: str, req_type: str) -> list[tuple[str, str]]:
    """Map an LLM requirement name to canonical names (D2, tokenized form).

    - any spelling of a known skill -> its canonical name ('REACT' -> React, 'Node JS' -> Node.js)
    - "A, B and C" -> all of them; "A/B/C" or "A or B" -> the alternatives we know
      ('Airflow/Flyte/Ray' -> Apache Airflow)
    - unknown names are kept as written (tidied), so nothing the posting asks is lost,
      and longer names are not shortened ('React Native' stays React Native, not React).
    """
    if req_type == "degree":
        return [("Degree", "degree")]
    if req_type == "years":
        return [("Experience", "years")]
    clean = " ".join(_PAREN.sub(" ", name).split()) or " ".join(name.split())
    whole = _known(clean)
    if whole and glossary().term(clean) is not None:
        return [whole]
    out: list[tuple[str, str]] = []
    for chunk in (c for c in _AND.split(clean) if c.strip()):
        alts = [a.strip() for a in _ALT.split(chunk) if a.strip()]
        known = [k for a in alts if (k := _known(a))]
        picked = known if known else [(glossary().canonical(chunk)[:60], req_type)]
        out += [k for k in picked if k not in out]
    return out


def parse_llm_requirements(items: Any, text: str) -> list[Requirement]:
    checker = EvidenceChecker(text)
    out: dict[str, Requirement] = {}
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or not checker.check(item.get("quote")):
            continue
        req_type = item["type"] if item.get("type") in TYPES else "tech"
        try:
            names = canonical_names(str(item["name"]), req_type)
            reqs = [
                Requirement(
                    name=name,
                    type=typ,  # type: ignore[arg-type]
                    importance="must" if item.get("importance") == "must" else "nice",
                    level=item.get("level") or None,
                    min_years=float(item["min_years"])
                    if item.get("min_years") is not None
                    else None,
                    evidence=Evidence(quote=str(item["quote"])[:500]),
                )
                for name, typ in names
            ]
        except (ValidationError, KeyError, TypeError, ValueError):
            continue
        for req in reqs:
            k = glossary().key_of(req.name)
            old = out.get(k)
            if old is None or (old.importance == "nice" and req.importance == "must"):
                out[k] = req
    return list(out.values())


def merge(primary: list[Requirement], backup: list[Requirement]) -> list[Requirement]:
    g = glossary()
    keys = {g.key_of(r.name) for r in primary}
    return primary + [r for r in backup if g.key_of(r.name) not in keys]


def _cached(p: Posting, gate: LLMGate) -> list[Requirement] | None:
    if p.requirements is None or p.text_hash != text_hash(p.full_text):
        return None
    if not (p.requirements_model or "").endswith(f"@{EXTRACTION_VERSION}"):
        return None
    if p.requirements_model == RULES_MODEL and gate.usable:
        return None  # upgrade rule-based results once the LLM is available
    return [Requirement.model_validate(r) for r in p.requirements]


async def ensure_requirements(
    postings: list[Posting], gate: LLMGate
) -> dict[int, list[Requirement]]:
    """Requirements for every posting; writes the cache fields on the Posting rows."""
    result: dict[int, list[Requirement]] = {}
    todo: list[Posting] = []
    for p in postings:
        cached = _cached(p, gate)
        if cached is not None:
            result[p.id] = cached
        else:
            todo.append(p)

    for i in range(0, len(todo), BATCH):
        batch = todo[i : i + BATCH]
        llm_reqs: dict[int, list[Requirement]] = {}
        if gate.usable:
            body = "\n\n".join(
                f'<posting id="{p.id}">\n{p.full_text[:MAX_TEXT_PER_POSTING]}\n</posting>'
                for p in batch
            )
            data = await gate.call_json(
                [
                    {"role": "system", "content": REQUIREMENTS_SYSTEM_PROMPT},
                    {"role": "user", "content": body},
                ],
                fast=True,
            )
            if isinstance(data, dict):
                texts = {p.id: p.full_text for p in batch}
                for entry in data.get("postings", []):
                    if isinstance(entry, dict) and entry.get("id") in texts:
                        pid = int(entry["id"])
                        llm_reqs[pid] = parse_llm_requirements(
                            entry.get("requirements"), texts[pid]
                        )
        for p in batch:
            rules = extract_requirements(p.full_text)
            if llm_reqs.get(p.id):
                reqs, model = (
                    merge(llm_reqs[p.id], rules),
                    f"{gate.model_label}@{EXTRACTION_VERSION}",
                )
            else:
                reqs, model = rules, RULES_MODEL
            p.requirements = [r.model_dump(mode="json") for r in reqs]
            p.requirements_model = model
            p.text_hash = text_hash(p.full_text)
            result[p.id] = reqs
    return result
