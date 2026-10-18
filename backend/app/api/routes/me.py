"""The current user: profile summary, search defaults, delete my data."""

from fastapi import APIRouter

from app.api.deps import SessionDep, UserDep
from app.api.presenters import user_out
from app.db.repos import cv_versions, searches, users
from app.schemas.auth import MeResponse, SettingsUpdate, User

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=MeResponse)
async def me(user: UserDep, s: SessionDep) -> MeResponse:
    return MeResponse(
        user=user_out(user),
        has_cv=await cv_versions.has_confirmed(s, user.id),
        latest_search_id=await searches.latest_id(s, user.id),
    )


@router.put("/settings", response_model=User)
async def update_settings(req: SettingsUpdate, user: UserDep, s: SessionDep) -> User:
    user = await s.merge(user)
    await users.set_defaults(s, user, req.titles, [p.model_dump() for p in req.places])
    await s.commit()
    return user_out(user)


@router.delete("", status_code=204)
async def delete_me(user: UserDep, s: SessionDep) -> None:
    """Delete my data: the account, sessions, CV versions, searches and results."""
    user = await s.merge(user)
    await users.delete_user(s, user)
    await s.commit()
