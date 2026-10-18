from typing import Annotated

from fastapi import APIRouter, Depends

from app import __version__
from app.config import Settings, get_settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(
        version=__version__,
        mock_mode=settings.mock_mode,
        nebius_configured=settings.nebius_configured,
        tavily_configured=settings.tavily_configured,
        model=settings.nemotron_model,
        fast_model=settings.nemotron_fast_model,
        vision_model=settings.nemotron_vision_model,
        ocr_enabled=settings.ocr_enabled,
    )
