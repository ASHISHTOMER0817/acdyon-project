"""
Firecrawl crawler adapter.

Primary path: Firecrawl scrape.
If Firecrawl is unconfigured or fails, a *permitted* plain HTTP GET is used
for public JSON/RSS/API URLs so the live demo can run without a Firecrawl
key. HTML sites without Firecrawl fall through to Selenium in the service.
"""

from __future__ import annotations

import json
import time
from typing import Optional

import httpx

from app.clients.firecrawl import FirecrawlClient, FirecrawlError
from app.config.logging import get_logger
from app.config.settings import Settings, get_settings
from app.crawlers.base import BaseCrawler, FetchResult

logger = get_logger(__name__)


class FirecrawlCrawler(BaseCrawler):
    """Primary fetcher with a conservative public-HTTP fallback for APIs."""

    name = "firecrawl"

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[FirecrawlClient] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or FirecrawlClient(self.settings)

    def fetch(self, url: str) -> FetchResult:
        """Try Firecrawl first; on failure, try a polite HTTP GET."""
        if self.client.available:
            try:
                payload = self.client.scrape(url)
                return FetchResult(
                    ok=True,
                    fetcher="firecrawl",
                    url=url,
                    html=payload.get("html") or "",
                    markdown=payload.get("markdown") or "",
                    http_status=payload.get("status_code"),
                    latency_ms=float(payload.get("latency_ms") or 0),
                    extras=payload.get("metadata") or {},
                )
            except FirecrawlError as exc:
                logger.warning("Firecrawl failed for %s: %s — trying HTTP GET", url, exc)

        return self._http_get(url)

    def _http_get(self, url: str) -> FetchResult:
        """
        Direct GET for public APIs / RSS.

        This is the demo-friendly path for RemoteOK / Arbeitnow style JSON.
        It is not a substitute for defeating bot walls.
        """
        headers = {
            "User-Agent": "job-ingestion-demo/0.1 (permitted public fetch; contact via repo)",
            "Accept": "application/json, application/rss+xml, application/xml, text/html;q=0.8",
        }
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.settings.request_timeout_seconds, follow_redirects=True) as http:
                response = http.get(url, headers=headers)
            latency_ms = (time.perf_counter() - started) * 1000

            if response.status_code == 429:
                return FetchResult(
                    ok=False,
                    fetcher="http",
                    url=url,
                    http_status=429,
                    latency_ms=latency_ms,
                    error="HTTP 429 rate limited — backing off, not retrying harder",
                )
            if response.status_code >= 400:
                return FetchResult(
                    ok=False,
                    fetcher="http",
                    url=url,
                    http_status=response.status_code,
                    latency_ms=latency_ms,
                    error=f"HTTP {response.status_code}",
                )

            body = response.text or ""
            markdown = body
            html = body if "html" in (response.headers.get("content-type") or "") else ""
            # Pretty-print JSON so Gemini sees readable listings.
            try:
                parsed = response.json()
                markdown = json.dumps(parsed, indent=2)[:200_000]
            except Exception:  # noqa: BLE001
                pass

            return FetchResult(
                ok=True,
                fetcher="http",
                url=url,
                html=html,
                markdown=markdown,
                text=body,
                http_status=response.status_code,
                latency_ms=latency_ms,
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - started) * 1000
            logger.warning("HTTP GET failed for %s: %s", url, exc)
            return FetchResult(
                ok=False,
                fetcher="http",
                url=url,
                latency_ms=latency_ms,
                error=str(exc),
            )
