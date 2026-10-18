"""Shared FastAPI dependencies: DB session, current user, app services."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import Database
from app.db.repos import users
from app.db.tables import User
from app.errors import AuthError
from app.events import EventBus
from app.runner import SearchRunner


def get_db(request: Request) -> Database:
    return request.app.state.db  # type: ignore[no-any-return]


def get_bus(request: Request) -> EventBus:
    return request.app.state.bus  # type: ignore[no-any-return]


def get_runner(request: Request) -> SearchRunner:
    return request.app.state.runner  # type: ignore[no-any-return]


async def get_session(db: Annotated[Database, Depends(get_db)]) -> AsyncIterator[AsyncSession]:
    """One session per request. Routes that write call `await session.commit()` themselves."""
    async with db.session() as s:
        yield s


def bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Sign in first.")
    return authorization[7:].strip()


async def authenticate(s: AsyncSession, authorization: str | None) -> User:
    user = await users.user_for_token(s, bearer_token(authorization))
    if user is None:
        raise AuthError("Your session has ended. Please sign in again.")
    return user


async def current_user(
    s: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    user = await authenticate(s, authorization)
    await s.commit()  # persist last_seen_at
    return user


SessionDep = Annotated[AsyncSession, Depends(get_session)]
UserDep = Annotated[User, Depends(current_user)]
