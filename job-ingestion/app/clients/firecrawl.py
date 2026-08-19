"""
Firecrawl HTTP client.

Primary fetcher in the design. When no API key is configured, `scrape()`
returns a structured error so the crawler can fall back to a permitted
plain-HTTP GET (public JSON/RSS) or Selenium — never an aggressive retry.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from app.config.logging import get_logger
from app.config.settings import Settings, get_settings
from app.utils.debug_dump import dump_firecrawl

logger = get_logger(__name__)


def _read_field(obj: Any, *keys: str, default: Any = None) -> Any:
    """Read a field from a dict or SDK object (e.g. DocumentMetadata)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        for key in keys:
            if key in obj and obj[key] is not None:
                return obj[key]
        return default
    for key in keys:
        if hasattr(obj, key):
            value = getattr(obj, key)
            if value is not None:
                return value
    return default


def _normalize_scrape_payload(payload: Any) -> dict[str, Any]:
    """
    Normalise firecrawl-py responses across SDK versions.

    Newer SDKs return typed objects (Document, DocumentMetadata) instead of
    plain dicts — calling `.get()` on metadata caused the error you saw.
    """
    if payload is None:
        return {}

    inner = _read_field(payload, "data", default=payload)
    if inner is None:
        inner = payload

    markdown = _read_field(inner, "markdown", default="") or ""
    html = _read_field(inner, "html", "rawHtml", "raw_html", default="") or ""
    metadata = _read_field(inner, "metadata", default={}) or {}

    status = (
        _read_field(metadata, "statusCode", "status_code")
        or _read_field(inner, "statusCode", "status_code")
        or 200
    )

    return {
        "markdown": markdown,
        "html": html,
        "status_code": int(status) if status else 200,
        "metadata": metadata,
    }


class FirecrawlError(Exception):
    """Raised when Firecrawl cannot return usable page content."""


class FirecrawlClient:
    """
    Thin wrapper around the official Firecrawl SDK.

    Responsibilities: timeout, retries with exponential backoff, and mapping
    SDK output into a plain dict (`html`, `markdown`, `status_code`).
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._app = None
        if self.settings.firecrawl_configured:
            try:
                from firecrawl import FirecrawlApp

                self._app = FirecrawlApp(api_key=self.settings.firecrawl_api_key)
            except Exception as exc:  # noqa: BLE001 — SDK import/init can fail
                logger.warning("Firecrawl SDK unavailable: %s", exc)
                self._app = None

    @property
    def available(self) -> bool:
        """True when the SDK was initialised with an API key."""
        return self._app is not None

    def scrape(self, url: str) -> dict[str, Any]:
        """
        Scrape `url` to HTML + Markdown.

        Retries on transient failures with exponential backoff. Does **not**
        increase request volume after a 429 — it waits, then retries a
        bounded number of times, then raises.
        """
        if not self.available:
            raise FirecrawlError("Firecrawl is not configured (missing API key)")

        last_error: Optional[Exception] = None
        attempts = self.settings.max_retries

        for attempt in range(1, attempts + 1):
            started = time.perf_counter()
            try:
                logger.info("Firecrawl scrape attempt %s/%s url=%s", attempt, attempts, url)
                result = self._scrape_once(url)
                elapsed_ms = (time.perf_counter() - started) * 1000
                result["latency_ms"] = elapsed_ms
                # Dump raw Firecrawl payload to temp/ for inspection.
                try:
                    dump_path = dump_firecrawl(url, result)
                    logger.debug("Firecrawl response saved to %s", dump_path)
                except Exception:  # noqa: BLE001
                    pass
                return result
            except FirecrawlError as exc:
                last_error = exc
                message = str(exc).lower()
                # Back off on rate limits; never hammer the source.
                if "429" in message or "rate" in message:
                    sleep_for = self.settings.backoff_base_seconds * (2 ** (attempt - 1))
                    logger.warning("Firecrawl rate-limited; sleeping %.1fs", sleep_for)
                    time.sleep(sleep_for)
                    continue
                # Non-retryable: auth, blocked, invalid URL.
                if any(token in message for token in ("401", "403", "captcha", "blocked")):
                    raise
                sleep_for = self.settings.backoff_base_seconds * (2 ** (attempt - 1))
                logger.warning("Firecrawl error (%s); retrying in %.1fs", exc, sleep_for)
                time.sleep(sleep_for)
            except Exception as exc:  # noqa: BLE001
                last_error = FirecrawlError(str(exc))
                sleep_for = self.settings.backoff_base_seconds * (2 ** (attempt - 1))
                logger.warning("Firecrawl unexpected error (%s); retrying in %.1fs", exc, sleep_for)
                time.sleep(sleep_for)

        raise FirecrawlError(str(last_error) if last_error else "Firecrawl scrape failed")

    def _scrape_once(self, url: str) -> dict[str, Any]:
        """Single SDK call. Normalises both v1 and v2 response shapes."""
        assert self._app is not None
        # firecrawl-py has changed the scrape signature across versions.
        try:
            payload = self._app.scrape_url(
                url,
                params={"formats": ["markdown", "html"]},
            )
        except TypeError:
            payload = self._app.scrape_url(url, formats=["markdown", "html"])

        if payload is None:
            raise FirecrawlError("Empty Firecrawl response")

        parsed = _normalize_scrape_payload(payload)
        markdown = parsed["markdown"]
        html = parsed["html"]

        if not markdown and not html:
            raise FirecrawlError("Firecrawl returned no html/markdown")

        return {
            "markdown": markdown,
            "html": html,
            "status_code": parsed["status_code"],
            "metadata": parsed["metadata"],
        }
