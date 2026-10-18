"""List Nemotron models available on Nebius Token Factory.

Usage (from backend/): uv run python scripts/list_models.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from app.config import get_settings  # noqa: E402


def main() -> int:
    s = get_settings()
    if not s.nebius_api_key:
        print("NEBIUS_API_KEY is not set (.env)")
        return 1
    r = httpx.get(
        f"{s.nebius_base_url.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {s.nebius_api_key}"},
        timeout=30,
    )
    r.raise_for_status()
    ids = sorted(m["id"] for m in r.json().get("data", []))
    for model_id in ids:
        if "nemotron" in model_id.lower():
            print(model_id)
    print(f"\n{len(ids)} models total. Current NEMOTRON_MODEL={s.nemotron_model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
