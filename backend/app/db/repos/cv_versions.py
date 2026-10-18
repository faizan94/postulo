"""CV versions (draft after upload, confirmed after review)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import CvVersion, utcnow
from app.errors import NotFoundError


async def create_draft(
    s: AsyncSession, user_id: int, label: str, source_type: str, text: str, ocr_used: bool
) -> CvVersion:
    cv = CvVersion(
        user_id=user_id,
        label=label[:200],
        source_type=source_type,
        clean_text=text,
        ocr_used=ocr_used,
        status="draft",
    )
    s.add(cv)
    await s.flush()
    return cv


async def get_owned(s: AsyncSession, user_id: int, cv_id: int) -> CvVersion:
    cv = await s.get(CvVersion, cv_id)
    if cv is None or cv.user_id != user_id:
        raise NotFoundError("CV version not found.")
    return cv


async def confirm(s: AsyncSession, cv: CvVersion, text: str, profile: dict[str, Any]) -> None:
    cv.clean_text = text
    cv.profile = profile
    cv.status = "confirmed"
    cv.confirmed_at = utcnow()


async def list_confirmed(s: AsyncSession, user_id: int) -> list[CvVersion]:
    rows = await s.scalars(
        select(CvVersion)
        .where(CvVersion.user_id == user_id, CvVersion.status == "confirmed")
        .order_by(CvVersion.created_at.desc())
    )
    return list(rows)


async def has_confirmed(s: AsyncSession, user_id: int) -> bool:
    row = await s.scalar(
        select(CvVersion.id)
        .where(CvVersion.user_id == user_id, CvVersion.status == "confirmed")
        .limit(1)
    )
    return row is not None
