"""The fixed places list for the place picker (D9)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.domain.places import places
from app.schemas.common import Place

router = APIRouter(prefix="/api/places", tags=["places"])


@router.get("", response_model=list[Place])
async def search_places(q: Annotated[str, Query(max_length=60)] = "") -> list[Place]:
    """Empty `q` returns popular places; otherwise prefix matches first."""
    return places().search(q)
