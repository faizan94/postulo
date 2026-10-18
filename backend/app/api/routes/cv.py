"""CV versions: upload or paste -> draft -> review -> confirm (D1, D11, D12)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.agents.profile import build_profile
from app.api.deps import SessionDep, UserDep
from app.api.presenters import cv_out
from app.config import Settings, get_settings
from app.db.repos import cv_versions
from app.schemas.cv import CvConfirm, CvConfirmed, CvDraft, CvVersion, SuggestedSearch
from app.services.intake import extract
from app.services.intake.router import MAX_BYTES

router = APIRouter(prefix="/api/cv", tags=["cv"])


@router.post("", response_model=CvDraft)
async def upload_cv(
    user: UserDep,
    s: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile | None, File(description="PDF or .docx")] = None,
    text: Annotated[str | None, Form(max_length=40_000)] = None,
) -> CvDraft:
    """Extract and clean the text. Nothing is used until the user confirms it."""
    data = await file.read(MAX_BYTES + 1) if file is not None else None
    result = extract(settings, filename=file.filename if file else None, data=data, text=text)
    cv = await cv_versions.create_draft(
        s, user.id, result.label, result.source_type, result.text, result.ocr_used
    )
    await s.commit()
    return CvDraft(
        cv_version_id=cv.id, text=result.text, ocr_used=result.ocr_used, warnings=result.warnings
    )


@router.put("/{cv_id}", response_model=CvConfirmed)
async def confirm_cv(
    cv_id: int,
    req: CvConfirm,
    user: UserDep,
    s: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> CvConfirmed:
    """Save the reviewed text and build the profile. Returns suggested titles and place."""
    cv = await cv_versions.get_owned(s, user.id, cv_id)
    profile, warnings = await build_profile(req.text, settings)
    await cv_versions.confirm(s, cv, req.text, profile.model_dump(mode="json"))
    await s.commit()
    return CvConfirmed(
        cv_version=cv_out(cv),
        profile=profile,
        suggested=SuggestedSearch(titles=profile.target_titles[:3], place=profile.place),
        warnings=warnings,
    )


@router.get("", response_model=list[CvVersion])
async def list_cvs(user: UserDep, s: SessionDep) -> list[CvVersion]:
    return [cv_out(cv) for cv in await cv_versions.list_confirmed(s, user.id)]


@router.delete("/{cv_id}", status_code=204)
async def delete_cv(cv_id: int, user: UserDep, s: SessionDep) -> None:
    cv = await cv_versions.get_owned(s, user.id, cv_id)
    await s.delete(cv)
    await s.commit()
