"""Async SQLite engine and session factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import event, update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.tables import Base, Search, utcnow


def _ensure_sqlite_dir(url: str) -> None:
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite" and parsed.database not in (None, "", ":memory:"):
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)  # type: ignore[arg-type]


class Database:
    def __init__(self, url: str) -> None:
        _ensure_sqlite_dir(url)
        self.engine = create_async_engine(url)
        if make_url(url).get_backend_name() == "sqlite":

            @event.listens_for(self.engine.sync_engine, "connect")
            def _pragmas(dbapi_conn: Any, _record: Any) -> None:
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA journal_mode=WAL")
                cur.execute("PRAGMA foreign_keys=ON")
                cur.execute("PRAGMA busy_timeout=5000")
                cur.close()

        self.sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_all(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def fail_stale_searches(self) -> int:
        """Searches left 'running' by a restart can never finish: mark them failed."""
        async with self.sessionmaker() as s:
            res = await s.execute(
                update(Search)
                .where(Search.status.in_(("queued", "running")))
                .values(
                    status="failed",
                    error="Search was interrupted, please re-run it.",
                    finished_at=utcnow(),
                )
            )
            await s.commit()
            return int(getattr(res, "rowcount", 0) or 0)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.sessionmaker() as s:
            yield s

    async def dispose(self) -> None:
        await self.engine.dispose()
