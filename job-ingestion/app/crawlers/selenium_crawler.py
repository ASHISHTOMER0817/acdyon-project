"""Selenium crawler adapter — browser fallback when the primary fetch fails."""

from __future__ import annotations

from typing import Optional

from app.clients.selenium import SeleniumClient, SeleniumError
from app.config.logging import get_logger
from app.config.settings import Settings, get_settings
from app.crawlers.base import BaseCrawler, FetchResult

logger = get_logger(__name__)


class SeleniumCrawler(BaseCrawler):
    """
    Browser-based recovery path.

    Invoked by IngestionService only after Firecrawl/HTTP is unhealthy.
    Stops on CAPTCHA rather than attempting to bypass it.
    """

    name = "selenium"

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[SeleniumClient] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or SeleniumClient(self.settings)

    def fetch(self, url: str) -> FetchResult:
        """Load the URL in Chrome. ok=False on driver/challenge/timeout errors."""
        try:
            payload = self.client.fetch(url)
            return FetchResult(
                ok=True,
                fetcher="selenium",
                url=url,
                html=payload.get("html") or "",
                markdown=payload.get("markdown") or "",
                http_status=payload.get("status_code"),
                latency_ms=float(payload.get("latency_ms") or 0),
                extras={
                    "title": payload.get("title"),
                    "final_url": payload.get("final_url"),
                },
            )
        except SeleniumError as exc:
            logger.warning("Selenium fallback failed for %s: %s", url, exc)
            return FetchResult(
                ok=False,
                fetcher="selenium",
                url=url,
                error=str(exc),
            )
