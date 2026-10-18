"""'How it works' judge view (D14): the agent trace, quiet drops and usage of one search."""

from fastapi import APIRouter

from app.api.deps import SessionDep, UserDep
from app.db.repos import searches
from app.schemas.search import DroppedPosting, HowResponse, TraceStep, Usage

router = APIRouter(prefix="/api/how", tags=["how"])


@router.get("/{search_id}", response_model=HowResponse)
async def how(search_id: int, user: UserDep, s: SessionDep) -> HowResponse:
    search = await searches.get_owned(s, user.id, search_id)
    return HowResponse(
        search_id=search.id,
        trace=[TraceStep.model_validate(t) for t in search.trace or []],
        dropped=[DroppedPosting.model_validate(d) for d in search.dropped or []],
        usage=Usage.model_validate(search.usage or {}),
    )
