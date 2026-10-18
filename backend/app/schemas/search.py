"""Searches, results, skill summary, Gap ROI and the judge view (§5.4, §7.3)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import Place, ShortText
from app.schemas.posting import JobCard

SearchStatus = Literal["queued", "running", "done", "failed"]
Stage = Literal["planning", "searching", "checking", "reading", "matching", "company", "ranking"]


class SearchCreate(BaseModel):
    cv_version_id: int
    titles: list[ShortText] = Field(min_length=1, max_length=3)
    places: list[Place] = Field(min_length=1, max_length=5)


class SearchCreated(BaseModel):
    search_id: int


class SkillSummaryItem(BaseModel):
    skill: str
    user_status: Literal["have", "related", "missing"]
    demand: int = Field(description="Jobs (of `of`) that ask for this skill")
    of: int
    must_count: int


class LearnNextItem(BaseModel):
    skill: str
    jobs_improved: int
    avg_gain_points: float
    unlocks: int = Field(description="Jobs that lose a cap or a must-have miss")
    slow: bool = Field(default=False, description="True for languages ('takes longer')")


class SearchSummary(BaseModel):
    """One row in the history list."""

    id: int
    status: SearchStatus
    cv_version_id: int | None
    titles: list[str]
    places: list[Place]
    result_count: int
    created_at: datetime
    finished_at: datetime | None = None


class SearchDetail(SearchSummary):
    """GET /api/searches/{id}. Safe to call while running (results are saved as they come)."""

    stage: Stage | None = None
    note: str | None = None
    error: str | None = None
    results: list[JobCard] = Field(default_factory=list)
    skill_summary: list[SkillSummaryItem] = Field(default_factory=list)
    learn_next: list[LearnNextItem] = Field(default_factory=list)


class TraceStep(BaseModel):
    at: datetime
    stage: Stage
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class DroppedPosting(BaseModel):
    title: str
    company: str | None = None
    url: str
    reason: str


class Usage(BaseModel):
    tavily_credits: int = 0
    llm_calls: int = 0


class HowResponse(BaseModel):
    """GET /api/how/{search_id}: the judge view (D14)."""

    search_id: int
    trace: list[TraceStep] = Field(default_factory=list)
    dropped: list[DroppedPosting] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
