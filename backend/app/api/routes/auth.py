"""Name-only login (D13). Works the same in mock and real mode (D18)."""

from typing import Annotated

from fastapi import APIRouter, Header

from app.api.deps import SessionDep, bearer_token
from app.api.presenters import user_out
from app.db.repos import users
from app.schemas.auth import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, s: SessionDep) -> LoginResponse:
    """Find or create the user by name and return a new session token."""
    user = await users.get_or_create(s, req.name)
    token = await users.create_session(s, user)
    await s.commit()
    return LoginResponse(token=token, user=user_out(user))


@router.post("/logout", status_code=204)
async def logout(s: SessionDep, authorization: Annotated[str | None, Header()] = None) -> None:
    await users.delete_session(s, bearer_token(authorization))
    await s.commit()
