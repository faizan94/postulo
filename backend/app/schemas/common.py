"""Shapes shared by several areas (PHASE1_PLAN.md §5.5)."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]

PlaceKind = Literal["city", "country", "region", "remote"]


class Place(BaseModel):
    """Where to search (D9, D22). From GET /api/places, or typed (an unknown city by name)."""

    kind: PlaceKind
    name: ShortText
    country_code: str | None = Field(default=None, min_length=2, max_length=2)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
    mock_mode: bool
    nebius_configured: bool
    tavily_configured: bool
    model: str
    fast_model: str
    vision_model: str
    ocr_enabled: bool


class Evidence(BaseModel):
    """A verbatim quote from the source text. Code checks it is really there (G2)."""

    quote: str = Field(min_length=1, max_length=500)
