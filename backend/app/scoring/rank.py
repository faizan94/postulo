"""The one sort key (D16): thin last, match high first, known date first, newest first."""

from app.schemas.posting import JobCard


def rank_key(card: JobCard) -> tuple[bool, int, bool, int]:
    value = card.match.value if card.match.value is not None else -1
    posted = card.posted_at.toordinal() if card.posted_at else 0
    return (card.match.thin, -value, card.posted_at is None, -posted)


def by_company_key(card: JobCard) -> tuple[int, tuple[bool, int, bool, int]]:
    value = card.company_score.value if card.company_score.value is not None else -1
    return (-value, rank_key(card))
