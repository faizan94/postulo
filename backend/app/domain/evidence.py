"""Quote checks (G2): an extracted item is only kept if its quote is really in the source."""

import re
import unicodedata

_WS = re.compile(r"\s+")
_HYPHEN_BREAK = re.compile(r"-\s*\n\s*")


def normalize(text: str) -> str:
    """NFKC, drop soft hyphens, join hyphenated line breaks, collapse whitespace, casefold."""
    t = unicodedata.normalize("NFKC", text).replace("­", "")
    t = _HYPHEN_BREAK.sub("", t)
    return _WS.sub(" ", t).casefold().strip()


class EvidenceChecker:
    """Normalises the source once, then checks many quotes against it."""

    def __init__(self, source: str) -> None:
        self._source = normalize(source)

    def check(self, quote: str | None) -> bool:
        if not quote:
            return False
        q = normalize(quote)
        return len(q) >= 2 and q in self._source


def snippet(text: str, start: int, end: int, max_len: int = 280) -> str:
    """A verbatim piece of `text` around [start, end), cut at sentence-ish boundaries.

    Always a substring of `text`, so it passes the quote check.
    """
    left = max(text.rfind(sep, 0, start) for sep in (". ", "; ", "\n", "•")) + 1
    right_candidates = [i for sep in (". ", "; ", "\n") if (i := text.find(sep, end)) != -1]
    right = min(right_candidates) if right_candidates else len(text)
    left = max(left, start - max_len // 2)
    right = min(right, end + max_len // 2)
    return text[left:right].strip(" \t•-–*·")
