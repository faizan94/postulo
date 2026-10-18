"""The candidate profile built from a confirmed CV (D3: no protected attributes)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Evidence, Place

SkillType = Literal["tech", "soft", "domain"]
Seniority = Literal["junior", "mid", "senior", "lead"]


class SkillItem(BaseModel):
    name: str = Field(description="Canonical name after the glossary, e.g. 'Kubernetes'")
    type: SkillType
    evidence: Evidence
    inferred: bool = Field(default=False, description="True if implied, not stated verbatim")


class Role(BaseModel):
    title: str
    company: str
    start: str | None = Field(default=None, description="YYYY-MM")
    end: str | None = Field(default=None, description="YYYY-MM or 'present'")
    evidence: Evidence


class LanguageItem(BaseModel):
    name: str
    level: str | None = Field(default=None, description="CEFR level or 'native', if stated")
    evidence: Evidence


class EducationItem(BaseModel):
    school: str
    degree: str | None = None
    evidence: Evidence


class Profile(BaseModel):
    headline: str | None = None
    summary: str | None = None
    skills: list[SkillItem] = Field(default_factory=list)
    roles: list[Role] = Field(default_factory=list)
    languages: list[LanguageItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    place: Place | None = None
    years_total: float | None = Field(default=None, description="Computed by code from roles")
    seniority: Seniority | None = Field(default=None, description="Computed by code")
    target_titles: list[str] = Field(default_factory=list, max_length=3)
