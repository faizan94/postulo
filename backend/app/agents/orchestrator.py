"""The search state machine (PHASE1_PLAN.md §5.6).

plan -> discover (Tavily) -> expand + quiet checks (board APIs) -> widen if thin (max 3 rounds,
inside the user's country) -> requirements -> match + score (cards stream) -> company score
-> rank + skill summary + Gap ROI. Results are saved as they come, so a reload never loses them.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.agents.discover import BoardsLike, Candidate, Dropped, SearchLike, discover, expand
from app.agents.llm_gate import LLMGate
from app.agents.planner import plan_queries, template_queries
from app.agents.requirements import ensure_requirements
from app.api import presenters
from app.config import Settings
from app.db.engine import Database
from app.db.repos import postings as postings_repo
from app.db.repos import searches as searches_repo
from app.db.tables import CvVersion, Posting, Search, utcnow
from app.domain.glossary import glossary
from app.domain.matching import match
from app.domain.places import JobLocation, places
from app.events import EventBus
from app.schemas.common import Place
from app.schemas.posting import SkillMatch
from app.schemas.profile import Profile
from app.scoring import company_score
from app.scoring.match_score import score
from app.scoring.rank import rank_key
from app.scoring.summary import learn_next, skill_summary

log = logging.getLogger(__name__)

MIN_GOOD = 5
MAX_ROUNDS = 3
MAX_CANDIDATES = 25
STAGE_TEXT = {
    "planning": "Planning your search",
    "searching": "Searching job boards",
    "checking": "Checking openings are still open",
    "reading": "Reading the full job posts",
    "matching": "Matching jobs to your skills",
    "company": "Looking at the companies",
    "ranking": "Ranking your best matches",
}


@dataclass
class RunContext:
    search_id: int
    db: Database
    bus: EventBus
    settings: Settings
    tavily: SearchLike
    boards: BoardsLike


@dataclass
class _Recorder:
    ctx: RunContext
    trace: list[dict[str, Any]] = field(default_factory=list)
    dropped: list[dict[str, Any]] = field(default_factory=list)
    credits: int = 0

    def log(self, stage: str, message: str, **data: Any) -> None:
        self.trace.append(
            {"at": datetime.now(UTC).isoformat(), "stage": stage, "message": message, "data": data}
        )

    async def stage(self, stage: str) -> None:
        self.ctx.bus.publish(
            self.ctx.search_id, {"type": "stage", "stage": stage, "message": STAGE_TEXT[stage]}
        )
        async with self.ctx.db.session() as s:
            search = await s.get(Search, self.ctx.search_id)
            if search is not None:
                search.stage = stage
                search.status = "running"
                await s.commit()

    def drop(self, items: list[Dropped]) -> None:
        for d in items:
            self.dropped.append(
                {"title": d.title, "company": d.company, "url": d.url, "reason": d.reason}
            )

    async def save_meta(self, s: Any, search: Search, llm_calls: int) -> None:
        search.trace = self.trace
        search.dropped = self.dropped
        search.usage = {"tavily_credits": self.credits, "llm_calls": llm_calls}


def _widen(
    wanted: list[Place], titles: list[str], tried: set[str]
) -> tuple[list[Place], list[str], str | None]:
    """Widening rule (Core, D9/D17): city -> its country, then related titles. Never abroad."""
    for p in wanted:
        wider = places().widen(p)
        if (
            wider
            and wider.name not in {w.name for w in wanted}
            and f"place:{wider.name}" not in tried
        ):
            tried.add(f"place:{wider.name}")
            return (
                [*wanted, wider],
                titles,
                f"Only a few matches in {p.name}, also showing {wider.name}.",
            )
    for t in titles:
        extra = [r for r in glossary().related_titles(t) if r not in titles]
        if extra and f"title:{t}" not in tried:
            tried.add(f"title:{t}")
            return (
                wanted,
                [*titles, *extra[:2]],
                f"Also showing related roles: {', '.join(extra[:2])}.",
            )
    return wanted, titles, None


async def _persist(s: Any, c: Candidate) -> Posting:
    j = c.job
    company = await postings_repo.upsert_company(
        s, j.company, ats=j.ats, board_slug=j.slug, domain=j.own_domain
    )
    found = places().place_of(JobLocation(j.location_text, j.country_code, j.remote))
    loc_place = found.model_dump() if found else None
    return await postings_repo.upsert_posting(
        s,
        j.url,
        ats=j.ats,
        board_slug=j.slug,
        external_id=j.external_id,
        company_id=company.id,
        title=j.title,
        location={
            "text": j.location_text,
            "country_code": j.country_code,
            "remote": j.remote,
            "place": loc_place,
        },
        workplace_type=j.workplace_type,
        posted_at=j.posted_at,
        apply_url=j.apply_url,
        full_text=j.text,
        status="open",
        last_checked_at=utcnow(),
        check_log=[{"check": "on_company_board", "result": "open", "at": utcnow().isoformat()}],
    )


async def run_search(ctx: RunContext) -> None:
    rec = _Recorder(ctx)
    gate = LLMGate(ctx.settings)
    try:
        async with ctx.db.session() as s:
            search = await s.get(Search, ctx.search_id)
            if search is None:
                return
            cv = await s.get(CvVersion, search.cv_version_id) if search.cv_version_id else None
            if cv is None or not cv.profile:
                raise ValueError("The CV for this search was deleted. Upload it again.")
            profile = Profile.model_validate(cv.profile)
            titles = list(search.titles)
            wanted = [Place.model_validate(p) for p in search.places]

        # 1. Plan
        await rec.stage("planning")
        queries, by_llm = await plan_queries(titles, wanted, profile, gate)
        rec.log(
            "planning",
            f"{len(queries)} queries ({'Nemotron' if by_llm else 'template'})",
            queries=[q.text for q in queries],
        )

        candidates: dict[str, Candidate] = {}
        tried: set[str] = set()
        note: str | None = None
        for round_no in range(1, MAX_ROUNDS + 1):
            # 2. Discover
            await rec.stage("searching")
            budget = ctx.settings.max_tavily_credits_per_run - rec.credits
            d = await discover(queries, ctx.tavily, budget, wanted)
            rec.credits += d.credits
            rec.log(
                "searching",
                f"Round {round_no}: {len(d.refs)} company boards found",
                boards=[f"{r.ats}:{r.slug}" for r in d.refs.values()],
                credits=d.credits,
            )
            # 3. Expand + quiet checks
            await rec.stage("checking")
            kept, dropped = await expand(
                d, ctx.boards, titles, wanted, ctx.settings.recent_days, set(candidates)
            )
            rec.drop(dropped)
            for c in kept:
                candidates.setdefault(c.job.url, c)
            rec.log("checking", f"{len(kept)} open matches kept, {len(dropped)} dropped quietly")
            if len(candidates) >= MIN_GOOD or round_no == MAX_ROUNDS:
                break
            if rec.credits >= ctx.settings.max_tavily_credits_per_run:
                rec.log("checking", "Tavily credit budget reached; stopping search")
                break
            wanted2, titles2, why = _widen(wanted, titles, tried)
            if why is None:
                break
            new_places = [p for p in wanted2 if p not in wanted]
            new_titles = [t for t in titles2 if t not in titles]
            wanted, titles = wanted2, titles2
            note = why
            ctx.bus.publish(ctx.search_id, {"type": "note", "message": why})
            rec.log("checking", f"Widening: {why}")
            # at most 2 extra queries per widening round, to save credits
            queries = template_queries(new_titles or titles[:1], new_places or wanted[:1])[:2]

        # 4. Read and store
        await rec.stage("reading")
        chosen = sorted(
            candidates.values(), key=lambda c: c.job.posted_at or datetime.min.date(), reverse=True
        )[:MAX_CANDIDATES]
        async with ctx.db.session() as s:
            rows = [await _persist(s, c) for c in chosen]
            await s.commit()
            # 5. Requirements + match, streaming each card
            await rec.stage("matching")
            reqs = await ensure_requirements(rows, gate)
            search = await s.get(Search, ctx.search_id)
            assert search is not None
            search.note = note
            matched: dict[int, list[SkillMatch]] = {}
            for p in rows:
                skills = match(profile, reqs[p.id])
                ms = score(skills, profile)
                matched[p.id] = skills
                breakdown = {
                    "match": ms.model_dump(mode="json"),
                    "skills": [m.model_dump(mode="json") for m in skills],
                }
                await searches_repo.upsert_result(s, ctx.search_id, p.id, ms.value, breakdown)
                await s.commit()
                result = await searches_repo.get_result(s, ctx.search_id, p.id)
                company = await postings_repo.get_company(s, p.company_id)
                assert result is not None
                card = presenters.job_card(result, p, company)
                ctx.bus.publish(
                    ctx.search_id, {"type": "job", "card": card.model_dump(mode="json")}
                )
            rec.log(
                "matching",
                f"Scored {len(rows)} jobs",
                requirements_by=sorted({p.requirements_model or "" for p in rows}),
            )
            if gate.enabled and gate.down_reason:
                rec.log(
                    "matching",
                    f"Nemotron unavailable ({gate.down_reason}); "
                    "used grounded rule-based extraction",
                )

            # 6. Company score (hiring activity + basics, D7)
            await rec.stage("company")
            by_company: dict[int, Candidate] = {}
            for c, p in zip(chosen, rows, strict=True):
                if p.company_id is not None:
                    by_company.setdefault(p.company_id, c)
            for company_id, c in by_company.items():
                company = await postings_repo.get_company(s, company_id)
                if company is None:
                    continue
                sig = company_score.CompanySignals(
                    c.board_size, c.newest_on_board, c.job.own_domain
                )
                value, band = company_score.score(sig)
                board = {"greenhouse": "Greenhouse", "lever": "Lever", "ashby": "Ashby"}[c.job.ats]
                sources = [
                    {
                        "title": f"{c.board_size} open roles on their {board} job board",
                        "url": c.job.url.rsplit("/", 2 if c.job.ats == "greenhouse" else 1)[0],
                        "date": c.newest_on_board.isoformat() if c.newest_on_board else None,
                    }
                ]
                if c.job.own_domain:
                    sources.append(
                        {
                            "title": f"Careers site on {c.job.own_domain}",
                            "url": f"https://{c.job.own_domain}",
                            "date": None,
                        }
                    )
                company.score, company.band, company.checked_at = value, band, utcnow()
                company.signals = {"open_roles": c.board_size, "sources": sources}
                cs = presenters.company_score(company)
                for p in rows:
                    if p.company_id == company_id:
                        ctx.bus.publish(
                            ctx.search_id,
                            {
                                "type": "company",
                                "posting_id": p.id,
                                "company_score": cs.model_dump(mode="json"),
                            },
                        )
            await s.commit()

            # 7. Rank, summary, Gap ROI
            await rec.stage("ranking")
            all_rows = await searches_repo.results_with_rows(s, ctx.search_id)
            cards = sorted((presenters.job_card(r, p, c) for r, p, c in all_rows), key=rank_key)
            top = cards[: ctx.settings.max_postings]
            await searches_repo.set_ranks(s, ctx.search_id, [c.posting_id for c in top])
            top_skills = [matched[c.posting_id] for c in top if c.posting_id in matched]
            search.summary = {
                "skills": [i.model_dump() for i in skill_summary(top_skills)],
                "learn_next": [i.model_dump() for i in learn_next(top_skills, profile)],
            }
            if not top:
                search.note = (note + " " if note else "") + (
                    "No open matching jobs right now. Try another title or place."
                )
            rec.log("ranking", f"Top {len(top)} of {len(cards)} jobs ranked")
            await rec.save_meta(s, search, gate.calls)
            await searches_repo.finish(s, search, "done")
            await s.commit()
        ctx.bus.publish(ctx.search_id, {"type": "done", "search_id": ctx.search_id})
    except Exception as e:  # the run must always end in a clear state
        log.exception("Search %s failed", ctx.search_id)
        message = (
            str(e)
            if isinstance(e, ValueError)
            else getattr(e, "message", None)
            or ("Something went wrong while searching. Please try again.")
        )
        async with ctx.db.session() as s:
            search = await s.get(Search, ctx.search_id)
            if search is not None:
                rec.log("ranking", f"Failed: {type(e).__name__}: {e}")
                await rec.save_meta(s, search, gate.calls)
                await searches_repo.finish(s, search, "failed", message)
                await s.commit()
        ctx.bus.publish(ctx.search_id, {"type": "error", "message": message})
    finally:
        if gate.down_reason and gate.enabled:
            log.info("Search %s used rule-based fallbacks: %s", ctx.search_id, gate.down_reason)
        ctx.bus.close(ctx.search_id)
