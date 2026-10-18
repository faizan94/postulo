"""Name-only login, the current user and their search defaults (D11, D13)."""

from pydantic import BaseModel, Field

from app.schemas.common import Place, ShortText


class LoginRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class User(BaseModel):
    id: int
    name: str
    default_titles: list[str] = Field(default_factory=list)
    default_places: list[Place] = Field(default_factory=list)


class LoginResponse(BaseModel):
    token: str
    user: User


class MeResponse(BaseModel):
    user: User
    has_cv: bool
    latest_search_id: int | None = None


class SettingsUpdate(BaseModel):
    titles: list[ShortText] = Field(min_length=1, max_length=3)
    places: list[Place] = Field(min_length=1, max_length=5)
