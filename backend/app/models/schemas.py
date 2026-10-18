"""API data shapes. Mirrors the MVP data shape in idea.md section 9."""

from typing import Literal

from pydantic import BaseModel, Field

SkillStatus = Literal["gold", "orange", "red"]
"""gold = you have it, orange = gap worth covering, red = important gap."""

LocationPref = Literal["Berlin", "Germany", "World"]


class Profile(BaseModel):
    name: str | None = None
    headline: str | None = Field(default=None, description="e.g. 'Data Engineer'")
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    years: float | None = Field(default=None, description="Years of professional experience")
    languages: list[str] = Field(
        default_factory=list, description="e.g. ['English C2', 'German B1']"
    )
    target_roles: list[str] = Field(default_factory=list, description="Roles to search for")
    location_pref: LocationPref | None = None


class Preferences(BaseModel):
    location: LocationPref = "Berlin"
    prompt: str = Field(
        default="",
        max_length=2000,
        description="Free text on top of the CV: 'I want X and Y, my strengths are...'",
    )


class Skill(BaseModel):
    name: str
    status: SkillStatus
    note: str | None = Field(default=None, description="Short evidence, e.g. quoted requirement")


class VerifiedFlags(BaseModel):
    company_exists: bool
    posting_live: bool
    recent: bool


class Posting(BaseModel):
    title: str
    company: str
    url: str
    posted: str | None = Field(default=None, description="ISO date, if known")
    location: str | None = None
    source: str | None = Field(default=None, description="Site it was found on, e.g. greenhouse.io")
    verified: VerifiedFlags
    score: float = Field(ge=0, le=5, description="Star score, 0-5 in 0.5 steps")
    skills: list[Skill] = Field(default_factory=list)
    why: str = ""


class RejectedPosting(BaseModel):
    """A posting the verify agent dropped (ghost job, dead link, stale...)."""

    title: str
    company: str | None = None
    url: str
    reason: str


class AgentStep(BaseModel):
    """One line of the agent trace shown in the UI/demo."""

    agent: Literal["orchestrator", "search", "verify", "score"]
    message: str
    duration_ms: int | None = None


class CVResponse(BaseModel):
    profile: Profile
    cv_text_chars: int = 0
    mock: bool = False


class SearchRequest(BaseModel):
    profile: Profile
    preferences: Preferences = Field(default_factory=Preferences)


class SearchResponse(BaseModel):
    profile: Profile
    postings: list[Posting]
    rejected: list[RejectedPosting] = Field(default_factory=list)
    trace: list[AgentStep] = Field(default_factory=list)
    mock: bool = False


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
    mock_mode: bool
    nebius_configured: bool
    tavily_configured: bool
    model: str
