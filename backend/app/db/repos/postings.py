"""Posting and company caches (not personal; they survive 'Delete my data')."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import Company, Posting


async def upsert_company(s: AsyncSession, name: str, **fields: Any) -> Company:
    key = " ".join(name.split()).casefold()
    company = await s.scalar(select(Company).where(Company.name_key == key))
    if company is None:
        company = Company(name_key=key, name=name, signals={}, band="pending")
        s.add(company)
    for k, v in fields.items():
        setattr(company, k, v)
    await s.flush()
    return company


async def upsert_posting(s: AsyncSession, url: str, **fields: Any) -> Posting:
    posting = await s.scalar(select(Posting).where(Posting.url == url))
    if posting is None:
        posting = Posting(url=url, **fields)
        s.add(posting)
    else:
        for k, v in fields.items():
            setattr(posting, k, v)
    await s.flush()
    return posting


async def get_posting(s: AsyncSession, posting_id: int) -> Posting | None:
    return await s.get(Posting, posting_id)


async def get_company(s: AsyncSession, company_id: int | None) -> Company | None:
    return await s.get(Company, company_id) if company_id is not None else None
