"""Postings -> requirements with verified quotes. LLM in batches of 5, rules as fallback.

Cached on the posting by text hash: the same posting text is never extracted twice.
"""

import hashlib
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

EXTRACTION_VERSION = "v3"  # bump when extraction logic changes: old cache entries re-run
RULES_MODEL = f"rules@{EXTRACTION_VERSION}"
BATCH = 5
MAX_TEXT_PER_POSTING = 8_000
TYPES = {"tech", "soft", "domain", "language", "years", "degree"}


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def canonical_names(name: str, req_type: str) -> list[tuple[str, str]]:
    """Map an LLM requirement name to canonical glossary names (D2).

    "Airflow/Flyte/Ray" -> [("Apache Airflow", "tech")]; "computer science degree" -> Degree.
    Names the glossary doesn't know are kept (short), so nothing the posting asks is lost.
    """
    g = glossary()
    if req_type == "degree":
        return [("Degree", "degree")]
    if req_type == "years":
        return [("Experience", "years")]
    hits = g.find(name)
    if hits:
        out: list[tuple[str, str]] = []
        for h in hits:
            t = "soft" if h.term.kind == "soft" else h.term.type
            if (h.term.name, t) not in out:
                out.append((h.term.name, t))
        return out
    return [(g.canonical(name)[:60], req_type)]


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
            old = out.get(req.name)
            if old is None or (old.importance == "nice" and req.importance == "must"):
                out[req.name] = req
    return list(out.values())


def merge(primary: list[Requirement], backup: list[Requirement]) -> list[Requirement]:
    names = {r.name for r in primary}
    return primary + [r for r in backup if r.name not in names]


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
