"""
Debug payload dumper.

Writes Firecrawl responses and Gemini request/response pairs to
`temp/<timestamp>_<label>.json` or `temp/<timestamp>_<label>.md` so you
can inspect exactly what each step produced without reading logs.

The `temp/` folder is in .gitignore — never committed.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Root of the project (two levels up from this file).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TEMP_DIR = _PROJECT_ROOT / "temp"


def _slug(url: str) -> str:
    """Short safe filename fragment from a URL."""
    return re.sub(r"[^a-zA-Z0-9]", "_", url)[:40].strip("_")


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def dump_firecrawl(url: str, payload: dict[str, Any]) -> Path:
    """
    Write the normalised Firecrawl response to temp/.

    Saves markdown and HTML in separate files so they are readable.
    Returns the path of the main JSON file.
    """
    _TEMP_DIR.mkdir(exist_ok=True)
    prefix = f"{_ts()}_firecrawl_{_slug(url)}"

    # Main JSON (metadata + stats, no huge body).
    summary = {
        "url": url,
        "status_code": payload.get("status_code"),
        "latency_ms": payload.get("latency_ms"),
        "markdown_len": len(payload.get("markdown") or ""),
        "html_len": len(payload.get("html") or ""),
        "metadata": payload.get("metadata"),
    }
    json_path = _TEMP_DIR / f"{prefix}_summary.json"
    json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    # Markdown body.
    if payload.get("markdown"):
        md_path = _TEMP_DIR / f"{prefix}_content.md"
        md_path.write_text(payload["markdown"], encoding="utf-8")

    # HTML body.
    if payload.get("html"):
        html_path = _TEMP_DIR / f"{prefix}_content.html"
        html_path.write_text(payload["html"], encoding="utf-8")

    return json_path


def dump_gemini(url: str, prompt: str, response_text: str) -> Path:
    """
    Write the Gemini prompt and raw response text to temp/.

    Returns the path of the response file.
    """
    _TEMP_DIR.mkdir(exist_ok=True)
    prefix = f"{_ts()}_gemini_{_slug(url)}"

    prompt_path = _TEMP_DIR / f"{prefix}_request.txt"
    prompt_path.write_text(prompt, encoding="utf-8")

    response_path = _TEMP_DIR / f"{prefix}_response.json"
    # Try to pretty-print if the response is valid JSON, else save as-is.
    try:
        parsed = json.loads(response_text)
        response_path.write_text(
            json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except (json.JSONDecodeError, TypeError):
        response_path.write_text(response_text or "", encoding="utf-8")

    return response_path
