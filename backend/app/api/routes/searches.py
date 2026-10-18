"""Searches: start, history, detail, live stream, re-run (§5.4)."""

import asyncio
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse

from app.agents.intent import parse_search
from app.agents.orchestrator import RunContext, run_search
from app.api import presenters
from app.api.deps import SessionDep, UserDep, authenticate, get_bus, get_db, get_runner
from app.config import Settings, get_settings
from app.db.engine import Database
from app.db.repos import cv_versions, searches, users
from app.db.tables import User
from app.errors import BadInputError
from app.events import EventBus, sse
from app.runner import SearchRunner
from app.schemas.search import (
    SearchCreate,
    SearchCreated,
    SearchDetail,
    SearchIntent,
    SearchParseRequest,
    SearchSummary,
)
from app.services.ats import BoardsService
from app.services.fakes import FakeBoards, FakeTavily
from app.services.tavily_client import TavilyService

router = APIRouter(prefix="/api/searches", tags=["searches"])

KEEPALIVE_SECONDS = 15


async def _run(ctx: RunContext) -> None:
    try:
        await run_search(ctx)
    finally:
        aclose = getattr(ctx.boards, "aclose", None)
        if aclose is not None:
            await aclose()
        tav_close = getattr(ctx.tavily, "__aexit__", None)
        if tav_close is not None:
            await tav_close(None, None, None)


async def _start(
    db: Database,
    bus: EventBus,
    runner: SearchRunner,
    settings: Settings,
    user: User,
    cv_version_id: int,
    titles: list[str],
    places: list[dict[str, Any]],
    keywords: list[str] | None = None,
) -> int:
    # Build services first: a missing key fails here with a clean 503, before any DB write.
    if settings.mock_mode:
        tavily: Any = FakeTavily()
        boards: Any = FakeBoards()
    else:
        tavily = TavilyService(settings)
        boards = BoardsService()
    async with db.session() as s:
        cv = await cv_versions.get_owned(s, user.id, cv_version_id)
        if cv.status != "confirmed":
            raise BadInputError("Please review and confirm your CV text first.")
        search = await searches.create(s, user.id, cv.id, titles, places, keywords)
        owner = await s.get(User, user.id)
        if owner is not None:
            await users.set_defaults(s, owner, titles, places)  # D11
        bus.open(search.id)  # before commit, so an early stream subscriber never misses events
        await s.commit()
        search_id = search.id
    runner.start(_run(RunContext(search_id, db, bus, settings, tavily, boards)))
    return search_id


@router.post("", response_model=SearchCreated)
async def create_search(
    req: SearchCreate,
    user: UserDep,
    db: Annotated[Database, Depends(get_db)],
    bus: Annotated[EventBus, Depends(get_bus)],
    runner: Annotated[SearchRunner, Depends(get_runner)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SearchCreated:
    search_id = await _start(
        db,
        bus,
        runner,
        settings,
        user,
        req.cv_version_id,
        list(req.titles),
        [p.model_dump() for p in req.places],
        list(req.keywords),
    )
    return SearchCreated(search_id=search_id)


@router.post("/parse", response_model=SearchIntent)
async def parse(
    req: SearchParseRequest, user: UserDep, settings: Annotated[Settings, Depends(get_settings)]
) -> SearchIntent:
    """Open search (D21): free text -> titles, places, keywords (editable in the UI)."""
    return await parse_search(req.text, settings)


@router.get("", response_model=list[SearchSummary])
async def history(user: UserDep, s: SessionDep) -> list[SearchSummary]:
    rows = await searches.list_for_user(s, user.id)
    counts = await searches.result_counts(s, [r.id for r in rows])
    return [presenters.search_summary(r, counts.get(r.id, 0)) for r in rows]


async def _detail(db: Database, user_id: int, search_id: int) -> SearchDetail:
    async with db.session() as s:
        search = await searches.get_owned(s, user_id, search_id)
        rows = await searches.results_with_rows(s, search_id)
        return presenters.search_detail(search, rows)


@router.get("/{search_id}", response_model=SearchDetail)
async def get_search(
    search_id: int, user: UserDep, db: Annotated[Database, Depends(get_db)]
) -> SearchDetail:
    return await _detail(db, user.id, search_id)


@router.post("/{search_id}/rerun", response_model=SearchCreated)
async def rerun(
    search_id: int,
    user: UserDep,
    s: SessionDep,
    db: Annotated[Database, Depends(get_db)],
    bus: Annotated[EventBus, Depends(get_bus)],
    runner: Annotated[SearchRunner, Depends(get_runner)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SearchCreated:
    old = await searches.get_owned(s, user.id, search_id)
    if old.cv_version_id is None:
        raise BadInputError("The CV for this search was deleted. Start a new search.")
    new_id = await _start(
        db,
        bus,
        runner,
        settings,
        user,
        old.cv_version_id,
        list(old.titles),
        list(old.places),
        list(old.keywords or []),
    )
    return SearchCreated(search_id=new_id)


@router.get("/{search_id}/events")
async def events(
    search_id: int,
    db: Annotated[Database, Depends(get_db)],
    bus: Annotated[EventBus, Depends(get_bus)],
    authorization: Annotated[str | None, Header()] = None,
) -> StreamingResponse:
    """Live stream: snapshot first, then replayed and new events; closes when done."""
    async with db.session() as s:
        user = await authenticate(s, authorization)
        await searches.get_owned(s, user.id, search_id)  # 404 for other users
        user_id = user.id

    async def stream() -> AsyncIterator[str]:
        sub = bus.subscribe(search_id)  # subscribe before the snapshot: no gap
        try:
            detail = await _detail(db, user_id, search_id)
            yield sse({"type": "snapshot", "search": detail.model_dump(mode="json")})
            terminal = detail.status in ("done", "failed")
            if terminal or sub is None:
                if detail.status == "failed":
                    yield sse({"type": "error", "message": detail.error or "Search failed."})
                else:
                    yield sse({"type": "done", "search_id": search_id})
                return
            replay, q = sub
            for ev in replay:
                yield sse(ev)
                if ev["type"] in ("done", "error"):
                    return
            while True:
                try:
                    item = await asyncio.wait_for(q.get(), timeout=KEEPALIVE_SECONDS)
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if item is None:
                    return
                yield sse(item)
                if item["type"] in ("done", "error"):
                    return
        finally:
            if sub is not None:
                bus.unsubscribe(search_id, sub[1])

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
