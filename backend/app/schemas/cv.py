"""CV versions: draft after upload, confirmed after review (D1, D12)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Place
from app.schemas.profile import Profile

SourceType = Literal["pdf", "docx", "image", "text"]
CvStatus = Literal["draft", "confirmed"]


class CvVersion(BaseModel):
    id: int
    label: str
    source_type: SourceType
    ocr_used: bool = False
    status: CvStatus
    created_at: datetime
    confirmed_at: datetime | None = None


class CvDraft(BaseModel):
    """POST /api/cv: extracted, cleaned text for the review screen."""

    cv_version_id: int
    text: str
    ocr_used: bool = False
    warnings: list[str] = Field(default_factory=list)


class CvConfirm(BaseModel):
    text: str = Field(min_length=50, max_length=20_000)


class SuggestedSearch(BaseModel):
    titles: list[str] = Field(default_factory=list, max_length=3)
    place: Place | None = None


class CvConfirmed(BaseModel):
    cv_version: CvVersion
    profile: Profile
    suggested: SuggestedSearch
    warnings: list[str] = Field(default_factory=list)
