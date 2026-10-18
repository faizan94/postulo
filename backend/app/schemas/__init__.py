"""Phase 1 API shapes. `frontend/src/lib/types.ts` mirrors these; change both together.

The legacy shapes in `app/models/schemas.py` stay until the old /api/cv and /api/jobs routes
are retired (M1/M2).
"""

from app.schemas.auth import LoginRequest, LoginResponse, MeResponse, SettingsUpdate, User
from app.schemas.common import Evidence, Place
from app.schemas.cv import CvConfirm, CvConfirmed, CvDraft, CvVersion, SuggestedSearch
from app.schemas.posting import (
    CompanyScore,
    CompanySource,
    JobCard,
    MatchScore,
    PostingDetail,
    Requirement,
    SkillMatch,
)
from app.schemas.profile import EducationItem, LanguageItem, Profile, Role, SkillItem
from app.schemas.search import (
    DroppedPosting,
    HowResponse,
    LearnNextItem,
    SearchCreate,
    SearchCreated,
    SearchDetail,
    SearchSummary,
    SkillSummaryItem,
    TraceStep,
    Usage,
)

__all__ = [
    "CompanyScore",
    "CompanySource",
    "CvConfirm",
    "CvConfirmed",
    "CvDraft",
    "CvVersion",
    "DroppedPosting",
    "EducationItem",
    "Evidence",
    "HowResponse",
    "JobCard",
    "LanguageItem",
    "LearnNextItem",
    "LoginRequest",
    "LoginResponse",
    "MatchScore",
    "MeResponse",
    "Place",
    "PostingDetail",
    "Profile",
    "Requirement",
    "Role",
    "SearchCreate",
    "SearchCreated",
    "SearchDetail",
    "SearchSummary",
    "SettingsUpdate",
    "SkillItem",
    "SkillMatch",
    "SkillSummaryItem",
    "SuggestedSearch",
    "TraceStep",
    "Usage",
    "User",
]
