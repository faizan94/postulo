from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.agents.orchestrator import extract_profile
from app.config import Settings, get_settings
from app.errors import BadInputError
from app.models.schemas import CVResponse
from app.services.cv_parser import MAX_PDF_BYTES, extract_text, is_pdf

router = APIRouter(prefix="/api", tags=["cv"])


@router.post("/cv", response_model=CVResponse)
async def upload_cv(
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File(description="CV as a PDF")],
    prompt: Annotated[str, Form(max_length=2000)] = "",
) -> CVResponse:
    """Upload a CV PDF and get back a structured profile. The CV is not stored."""
    data = await file.read(MAX_PDF_BYTES + 1)
    if settings.mock_mode:
        if not is_pdf(data):
            raise BadInputError("The uploaded file is not a PDF.")
        try:
            chars = len(extract_text(data))
        except BadInputError:
            chars = 0
        profile = await extract_profile("", settings, prompt)
        return CVResponse(profile=profile, cv_text_chars=chars, mock=True)

    text = extract_text(data)
    if len(text) < 50:
        raise BadInputError(
            "Could not find text in this PDF (is it a scanned image?). Try a text-based PDF."
        )
    profile = await extract_profile(text, settings, prompt)
    return CVResponse(profile=profile, cv_text_chars=len(text))
