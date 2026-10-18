"""Pick the reader by file type (D1, D19).

PDF -> best of pypdf-layout / pdfium / pypdf-plain; if still poor, Nemotron vision reads the
pages. .docx -> python-docx. PNG/JPG/WebP -> Nemotron vision. Pasted text -> as is.
"""

import io
from dataclasses import dataclass, field

from docx import Document

from app.config import Settings
from app.errors import BadInputError
from app.services.intake.clean_text import clean
from app.services.intake.ocr import normalise_image, ocr_images, vision_available
from app.services.intake.pdf import extract_pdf, render_pages, words

MAX_BYTES = 10 * 1024 * 1024
MAX_TEXT = 20_000
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")
SCAN_MESSAGE = (
    "This looks like a scan or photo and we couldn't read it. "
    "Please upload a text PDF or .docx, or paste the text."
)


@dataclass
class ExtractResult:
    text: str
    source_type: str
    label: str
    ocr_used: bool = False
    warnings: list[str] = field(default_factory=list)
    method: str = ""


def _docx(data: bytes) -> str:
    try:
        doc = Document(io.BytesIO(data))
    except Exception as e:  # python-docx raises several types for broken files
        raise BadInputError("Could not read the Word file. Save it again as .docx or PDF.") from e
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(dict.fromkeys(cells)))
    return "\n".join(parts)


async def _pdf(data: bytes, settings: Settings) -> tuple[str, bool, str]:
    """(text, ocr_used, method)."""
    best = extract_pdf(data)
    if not best.poor:
        return best.text, False, best.method
    if vision_available(settings):
        ocr = await ocr_images(render_pages(data), settings)
        if ocr and len(words(ocr)) >= len(words(best.text)):
            return ocr, True, "nemotron-vision"
    if len(best.text) < 50:
        raise BadInputError(SCAN_MESSAGE)
    return best.text, False, best.method


async def extract(
    settings: Settings,
    *,
    filename: str | None = None,
    data: bytes | None = None,
    text: str | None = None,
) -> ExtractResult:
    ocr_used, method = False, "text"
    if text is not None and text.strip():
        raw, source, label = text, "text", "Pasted text"
    elif data is not None:
        if not data:
            raise BadInputError("The uploaded file is empty.")
        if len(data) > MAX_BYTES:
            raise BadInputError("The file is larger than 10 MB.")
        name = (filename or "cv").strip() or "cv"
        lower = name.lower()
        label = name
        if data[:5] == b"%PDF-":
            raw, ocr_used, method = await _pdf(data, settings)
            source = "pdf"
        elif data[:2] == b"PK" and lower.endswith(".docx"):
            raw, source, method = _docx(data), "docx", "python-docx"
        elif lower.endswith(".doc"):
            raise BadInputError("Old .doc files aren't supported. Save it as PDF or .docx.")
        elif lower.endswith(IMAGE_EXT):
            if not vision_available(settings):
                raise BadInputError(SCAN_MESSAGE)
            try:
                png = normalise_image(data)
            except ValueError as e:
                raise BadInputError("Could not read this image.") from e
            ocr = await ocr_images([png], settings)
            if not ocr:
                raise BadInputError(SCAN_MESSAGE)
            raw, source, ocr_used, method = ocr, "image", True, "nemotron-vision"
        else:
            raise BadInputError("Upload a PDF, .docx or an image (PNG/JPG), or paste the text.")
    else:
        raise BadInputError("Upload a file or paste your CV text.")

    warnings: list[str] = []
    if ocr_used:
        warnings.append("We read this CV from the page images. Please check the text carefully.")
    cleaned = clean(raw)
    if len(cleaned) > MAX_TEXT:
        cleaned = cleaned[:MAX_TEXT]
        warnings.append("Your CV was long, so only the first 20,000 characters are used.")
    if len(cleaned) < 50:
        raise BadInputError("We found almost no text in this CV.")
    return ExtractResult(cleaned, source, label, ocr_used, warnings, method)
