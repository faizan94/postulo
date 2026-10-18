"""Job detail: full post text, apply link, match breakdown, company score (D15)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api import presenters
from app.api.deps import SessionDep, UserDep
from app.db.repos import postings, searches
from app.errors import NotFoundError
from app.schemas.posting import PostingDetail

router = APIRouter(prefix="/api/postings", tags=["postings"])


@router.get("/{posting_id}", response_model=PostingDetail)
async def get_posting(
    posting_id: int, search_id: Annotated[int, Query()], user: UserDep, s: SessionDep
) -> PostingDetail:
    await searches.get_owned(s, user.id, search_id)
    result = await searches.get_result(s, search_id, posting_id)
    posting = await postings.get_posting(s, posting_id)
    if result is None or posting is None:
        raise NotFoundError("This job is not part of that search.")
    company = await postings.get_company(s, posting.company_id)
    return presenters.posting_detail(result, posting, company)
