"""Users and name-only sessions (D13)."""

import hashlib
import re
import secrets
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import Session, User, utcnow
from app.errors import BadInputError

_NAME_RE = re.compile(r"^[\w \-]{2,40}$")


def normalize_name(raw: str) -> tuple[str, str]:
    """Return (display name, lookup key). Raises BadInputError for invalid names."""
    display = " ".join(raw.split())
    if not _NAME_RE.fullmatch(display):
        raise BadInputError("Use 2-40 letters, digits, spaces, '-' or '_' for your name.")
    return display, display.casefold()


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def get_or_create(s: AsyncSession, raw_name: str) -> User:
    display, key = normalize_name(raw_name)
    user = await s.scalar(select(User).where(User.name_key == key))
    if user is None:
        user = User(name_key=key, display_name=display, default_titles=[], default_places=[])
        s.add(user)
        await s.flush()
    return user


async def create_session(s: AsyncSession, user: User) -> str:
    token = secrets.token_urlsafe(32)
    s.add(Session(token_hash=_hash(token), user_id=user.id))
    await s.flush()
    return token


async def user_for_token(s: AsyncSession, token: str) -> User | None:
    sess = await s.get(Session, _hash(token))
    if sess is None:
        return None
    sess.last_seen_at = utcnow()
    return await s.get(User, sess.user_id)


async def delete_session(s: AsyncSession, token: str) -> None:
    await s.execute(delete(Session).where(Session.token_hash == _hash(token)))


async def set_defaults(
    s: AsyncSession, user: User, titles: list[str], places: list[dict[str, Any]]
) -> None:
    user.default_titles = list(titles)
    user.default_places = list(places)


async def delete_user(s: AsyncSession, user: User) -> None:
    """Delete my data: FKs cascade to sessions, CV versions, searches and results."""
    await s.delete(user)
