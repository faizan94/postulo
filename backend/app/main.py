"""FastAPI entrypoint. Run: `uv run uvicorn app.main:app --reload`."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routes import cv, health, jobs
from app.config import get_settings
from app.errors import PostuloError

log = logging.getLogger("app")


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    app = FastAPI(
        title="Postulo API",
        version=__version__,
        description="AI job-application agent: CV -> verified, scored job postings.",
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

    app.include_router(health.router)
    app.include_router(cv.router)
    app.include_router(jobs.router)

    if settings.mock_mode:
        log.info("MOCK_MODE is on: endpoints return fake data, no API calls are made.")
    return app


app = create_app()
