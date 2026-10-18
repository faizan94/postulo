from typing import Annotated

from fastapi import APIRouter, Depends

from app.agents.orchestrator import run_job_search
from app.config import Settings, get_settings
from app.models.schemas import SearchRequest, SearchResponse

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("/search", response_model=SearchResponse)
async def search_jobs(
    req: SearchRequest, settings: Annotated[Settings, Depends(get_settings)]
) -> SearchResponse:
    """Profile + preferences -> verified, scored postings (search -> verify -> score)."""
    return await run_job_search(req.profile, req.preferences, settings)
