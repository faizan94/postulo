"""Nemotron 3.5 Super VL reads CV page images (D19). Text only; photos are never described."""

import asyncio
import base64
import io
import logging

from PIL import Image

from app.agents.prompts.ocr import OCR_SYSTEM_PROMPT
from app.config import Settings
from app.errors import PostuloError
from app.services.llm import LLMClient

log = logging.getLogger(__name__)
MAX_SIDE = 2000


def vision_available(settings: Settings) -> bool:
    return settings.ocr_enabled and not settings.mock_mode and bool(settings.nebius_api_key)


def normalise_image(data: bytes) -> bytes:
    """Any supported image -> PNG with the longest side <= 2000 px."""
    try:
        opened = Image.open(io.BytesIO(data))
        opened.load()
    except Exception as e:  # PIL raises many types for broken files
        raise ValueError("unreadable image") from e
    img = opened.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def ocr_images(images: list[bytes], settings: Settings) -> str | None:
    """Transcribe page images in order. None if the vision model fails."""

    async def one(llm: LLMClient, png: bytes) -> str:
        b64 = base64.b64encode(png).decode()
        return await llm.chat(
            [
                {"role": "system", "content": OCR_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Transcribe this CV page."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ],
                },
            ],
            model=settings.nemotron_vision_model,
            reasoning="off",
            temperature=0.6,
            max_tokens=4000,
        )

    try:
        async with LLMClient(settings) as llm:
            pages = await asyncio.gather(*(one(llm, img) for img in images))
    except PostuloError as e:
        log.warning("Vision OCR failed: %s", e.message)
        return None
    return "\n\n".join(p.strip() for p in pages if p.strip()) or None
