"""CV intake: file or pasted text -> cleaned plain text (PHASE1_PLAN.md §5.7)."""

from app.services.intake.router import ExtractResult, extract

__all__ = ["ExtractResult", "extract"]
