"""Command line: run the whole agent pipeline without the frontend.

    uv run python -m app cv path/to/cv.pdf
    uv run python -m app run path/to/cv.pdf --location Berlin --prompt "data roles" [--mock]

`run` writes output/{date}/profile.json, results.json and briefing.md. Handy for tuning
prompts and for caching demo results. (CLI + dated output folder pattern adapted from
mathcrypto/ai-agent-orchestrator.)
"""

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

from app.agents.orchestrator import extract_profile, run_job_search
from app.config import Settings, get_settings
from app.errors import PostuloError
from app.models.schemas import Preferences, Profile, SearchResponse
from app.services.cv_parser import extract_text


def render_briefing(resp: SearchResponse, run_date: str) -> str:
    """The user-facing briefing (idea.md step 6) as Markdown."""
    p = resp.profile
    lines = [f"# Postulo briefing - {run_date}", ""]
    who = " · ".join(x for x in (p.name, p.headline) if x) or "Candidate"
    lines += [f"**{who}**", ""]
    if resp.mock:
        lines += ["> Mock data (MOCK_MODE=true).", ""]
    if not resp.postings:
        lines += ["No verified postings found. Try a wider location or another prompt.", ""]
    for i, post in enumerate(resp.postings, 1):
        gold = [s.name for s in post.skills if s.status == "gold"]
        orange = [s.name for s in post.skills if s.status == "orange"]
        red = [s.name for s in post.skills if s.status == "red"]
        lines += [
            f"## {i}. {post.title} - {post.company}  ({post.score:.1f}/5)",
            f"- **Link:** {post.url}",
            f"- **Where / when:** {post.location or 'n/a'} · posted {post.posted or 'n/a'}",
            f"- 🟡 **Match:** {', '.join(gold) or '-'}",
            f"- 🟠 **Gap worth covering:** {', '.join(orange) or '-'}",
            f"- 🔴 **Important gap:** {', '.join(red) or '-'}",
            f"- **Why:** {post.why}",
            "",
        ]
    strong = [x for x in resp.postings if x.score >= 4]
    reds = sorted({s.name for x in resp.postings for s in x.skills if s.status == "red"})
    lines += ["## Verdict", ""]
    if strong:
        lines.append("Apply to: " + ", ".join(f"{x.company} ({x.title})" for x in strong) + ".")
    if reds:
        lines.append("Covering these gaps would open more doors: " + ", ".join(reds) + ".")
    if resp.rejected:
        lines += ["", f"## Removed ({len(resp.rejected)} ghost/dead postings)", ""]
        lines += [f"- ~~{r.title}~~ ({r.company or '?'}): {r.reason}" for r in resp.rejected]
    return "\n".join(lines) + "\n"


async def _profile_from_pdf(data: bytes, prompt: str, settings: Settings) -> Profile:
    text = "" if settings.mock_mode else extract_text(data)
    return await extract_profile(text, settings, prompt)


async def _run(args: argparse.Namespace, cv_bytes: bytes, settings: Settings) -> int:
    profile = await _profile_from_pdf(cv_bytes, args.prompt, settings)
    if args.command == "cv":
        print(profile.model_dump_json(indent=2))
        return 0

    prefs = Preferences(location=args.location, prompt=args.prompt)
    resp = await run_job_search(profile, prefs, settings)
    for step in resp.trace:
        print(f"[{step.agent}] {step.message}")

    out_dir = Path(args.out) / args.date
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "profile.json").write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "results.json").write_text(resp.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "briefing.md").write_text(render_briefing(resp, args.date), encoding="utf-8")
    print(f"\n{len(resp.postings)} postings -> {out_dir}")
    for name in ("profile.json", "results.json", "briefing.md"):
        print(f"  {name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app", description="Postulo agent CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("cv", "CV PDF -> profile JSON"), ("run", "Full pipeline")):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("cv", help="Path to the CV PDF")
        cmd.add_argument("--prompt", default="", help="Extra wishes on top of the CV")
        cmd.add_argument("--mock", action="store_true", help="Force MOCK_MODE (no API calls)")
        if name == "run":
            cmd.add_argument("--location", choices=["Berlin", "Germany", "World"], default="Berlin")
            cmd.add_argument("--date", default=date.today().isoformat())
            cmd.add_argument("--out", default="output", help="Output root folder")
    args = parser.parse_args(argv)

    settings = get_settings()
    if args.mock:
        settings = settings.model_copy(update={"mock_mode": True})
    try:
        return asyncio.run(_run(args, Path(args.cv).read_bytes(), settings))
    except PostuloError as e:
        print(f"error ({e.code}): {e.message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
