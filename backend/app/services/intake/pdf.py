"""PDF text: try several extractors and keep the best (D19).

Measured on a real CV: pypdf's default mode returned one word per line (1,147 lines of ~3
chars); pypdf layout mode and pdfium rebuilt 68 clean lines with the same words. Layout mode can
put two columns on one line, so lines are split at a shared column gap.
"""

import io
import re
from collections import Counter
from dataclasses import dataclass

import pypdfium2 as pdfium
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.errors import BadInputError

MAX_PAGES = 10
_WORD = re.compile(r"[A-Za-zÄÖÜäöüß+#]{2,}")
_GAP = re.compile(r"\S( {4,})\S")


@dataclass
class PdfText:
    text: str
    method: str
    pages: int
    quality: float  # 0-100
    poor: bool  # too little or badly broken text: try vision


def words(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text)}


def split_columns(page: str) -> str:
    """If many lines share a wide gap at the same column, read left column then right."""
    lines = page.splitlines()
    # The right column starts at the same x on every line, so count where gaps END.
    ends: Counter[int] = Counter()
    for ln in lines:
        for m in _GAP.finditer(ln):
            ends[m.end(1)] += 1
    content = [ln for ln in lines if ln.strip()]
    if not ends or not content:
        return page
    col, hits = ends.most_common(1)[0]
    if hits < max(4, len(content) * 0.35):
        return page
    left, right = [], []
    for ln in lines:
        if len(ln) > col and ln[col - 2 : col] == "  ":
            left.append(ln[:col])
            right.append(ln[col:])
        else:
            left.append(ln)
    return "\n".join(left + [""] + right)


def _tidy(text: str) -> str:
    out = [re.sub(r"[ \t]{2,}", " ", ln).strip() for ln in text.splitlines()]
    tidy: list[str] = []
    for ln in out:
        if ln or (tidy and tidy[-1]):
            tidy.append(ln)
    return "\n".join(tidy).strip()


def quality(text: str, all_words: set[str]) -> float:
    """Word coverage (vs. the union of all extractors) minus a penalty for broken lines."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines or not all_words:
        return 0.0
    coverage = len(words(text) & all_words) / len(all_words)
    avg = sum(len(ln) for ln in lines) / len(lines)
    penalty = max(0.0, 15 - avg) * 4 + max(0.0, avg - 250) * 0.2
    return max(0.0, round(coverage * 100 - penalty, 1))


def pick_best(candidates: list[tuple[str, str]]) -> tuple[str, str, float]:
    """(text, method, quality) of the best candidate."""
    union: set[str] = set()
    for _name, t in candidates:
        union |= words(t)
    scored = [(quality(t, union), name, t) for name, t in candidates if t.strip()]
    if not scored:
        return "", "none", 0.0
    q, name, t = max(scored, key=lambda x: x[0])
    return t, name, q


def extract_pdf(data: bytes) -> PdfText:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise BadInputError("The PDF is password-protected.")
        pages = reader.pages[:MAX_PAGES]
        layout = "\n\n".join(
            _tidy(split_columns(p.extract_text(extraction_mode="layout") or "")) for p in pages
        )
        plain = "\n\n".join(_tidy(p.extract_text() or "") for p in pages)
        n_pages = len(pages)
    except PdfReadError as e:
        raise BadInputError(f"Could not read the PDF: {e}") from e
    candidates = [("pypdf-layout", layout), ("pypdf-plain", plain)]
    try:
        doc = pdfium.PdfDocument(data)
        texts = [doc[i].get_textpage().get_text_bounded() for i in range(min(len(doc), MAX_PAGES))]
        candidates.append(("pdfium", "\n\n".join(_tidy(t) for t in texts)))
    except pdfium.PdfiumError:
        pass
    text, method, q = pick_best(candidates)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    avg = sum(len(ln) for ln in lines) / max(1, len(lines))
    poor = len(text) < 100 * max(1, n_pages) or avg < 12
    return PdfText(text=text, method=method, pages=n_pages, quality=q, poor=poor)


def render_pages(data: bytes, max_pages: int = 4, scale: float = 2.0) -> list[bytes]:
    """PNG bytes per page for vision OCR."""
    doc = pdfium.PdfDocument(data)
    out = []
    for i in range(min(len(doc), max_pages)):
        img = doc[i].render(scale=scale).to_pil()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        out.append(buf.getvalue())
    return out
