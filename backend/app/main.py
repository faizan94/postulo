"""FastAPI entrypoint. Run: `uv run uvicorn app.main:app --reload`."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routes import auth, cv, health, how, me, places, postings, searches
from app.config import Settings, get_settings
from app.db.engine import Database
from app.errors import PostuloError
from app.events import EventBus
from app.runner import SearchRunner

log = logging.getLogger("app")


def _settings(app: FastAPI) -> Settings:
    """Honour test overrides of get_settings in the lifespan too."""
    return app.dependency_overrides.get(get_settings, get_settings)()  # type: ignore[no-any-return]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = _settings(app)
    db = Database(settings.database_url)
    await db.create_all()
    stale = await db.fail_stale_searches()
    if stale:
        log.info("Marked %d interrupted searches as failed", stale)
    app.state.db = db
    app.state.bus = EventBus()
    app.state.runner = SearchRunner()
    if settings.mock_mode:
        log.info("MOCK_MODE is on: fake Tavily and job boards, no external API calls.")
    try:
        yield
    finally:
        await app.state.runner.shutdown()
        await db.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    app = FastAPI(
        title="Postulo API",
        version=__version__,
        description="AI job search: CV -> open, recent jobs with match and company scores.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(PostuloError)
    async def postulo_error_handler(_: Request, exc: PostuloError) -> JSONResponse:
        log.warning("%s: %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    for module in (health, auth, me, places, cv, searches, postings, how):
        app.include_router(module.router)
    return app


app = create_app()
