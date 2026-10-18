"""CV PDF -> plain text via pypdf.

Extension point: Nemotron 3.5 Super VL can read the PDF pages as images (better on
designed/two-column CVs). Rasterise pages and send them as image_url parts via LLMClient.
"""

import io
import logging

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.errors import BadInputError

log = logging.getLogger(__name__)

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PAGES = 10


def is_pdf(data: bytes) -> bool:
    return data[:5] == b"%PDF-"


def extract_text(data: bytes) -> str:
    """Return the CV text. Raises BadInputError for non-PDFs, huge files or unreadable PDFs."""
    if not data:
        raise BadInputError("The uploaded file is empty.")
    if len(data) > MAX_PDF_BYTES:
        raise BadInputError("The PDF is larger than 10 MB.")
    if not is_pdf(data):
        raise BadInputError("The uploaded file is not a PDF.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise BadInputError("The PDF is password-protected.")
        pages = [page.extract_text() or "" for page in reader.pages[:MAX_PAGES]]
    except PdfReadError as e:
        raise BadInputError(f"Could not read the PDF: {e}") from e
    text = "\n\n".join(p.strip() for p in pages if p.strip())
    log.debug("Extracted %d chars from %d pages", len(text), len(pages))
    return text
