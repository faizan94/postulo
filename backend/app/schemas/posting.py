"""Job postings, requirements, skill matches and the two scores (§5.5, §7)."""

import datetime as dt
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Evidence, Place

RequirementType = Literal["tech", "soft", "domain", "language", "years", "degree"]
Importance = Literal["must", "nice"]
SkillStatus = Literal["have", "related", "missing_nice", "missing_must"]
CompanyBand = Literal["strong", "okay", "weak", "not_enough_data", "pending"]
WorkplaceType = Literal["onsite", "hybrid", "remote"]


class Requirement(BaseModel):
    name: str = Field(description="Canonical (English) name")
    type: RequirementType
    importance: Importance
    level: str | None = None
    min_years: float | None = None
    evidence: Evidence


class SkillMatch(BaseModel):
    requirement: Requirement
    status: SkillStatus
    cv_evidence: Evidence | None = None


class MatchScore(BaseModel):
    value: int | None = Field(default=None, ge=0, le=100, description="null when thin")
    must_met: str = Field(description="e.g. '6/8'")
    nice_met: str
    gates_applied: list[str] = Field(default_factory=list)
    thin: bool = False


class CompanySource(BaseModel):
    title: str
    url: str
    date: dt.date | None = None


class CompanyScore(BaseModel):
    value: int | None = Field(default=None, ge=0, le=100)
    band: CompanyBand
    sources: list[CompanySource] = Field(default_factory=list)


class JobCard(BaseModel):
    posting_id: int
    title: str
    company: str
    place: Place | None = None
    workplace_type: WorkplaceType | None = None
    posted_at: date | None = None
    match: MatchScore
    company_score: CompanyScore
    top_skills: list[SkillMatch] = Field(default_factory=list, max_length=6)
    related_role: bool = Field(default=False, description="Same role family, not the exact title")


class PostingDetail(BaseModel):
    """GET /api/postings/{id}?search_id=: everything on the job detail page."""

    posting_id: int
    title: str
    company: str
    place: Place | None = None
    workplace_type: WorkplaceType | None = None
    posted_at: date | None = None
    url: str
    apply_url: str
    full_text: str = Field(description="Plain text as fetched, never rewritten (D15)")
    match: MatchScore
    skills: list[SkillMatch] = Field(default_factory=list)
    company_score: CompanyScore
    related_role: bool = False
