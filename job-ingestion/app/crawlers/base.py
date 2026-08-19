"""
Crawler interface.

Each source/fetcher implements `fetch(url) -> FetchResult`. The ingestion
service decides when to fail over; crawlers only retrieve bytes/text.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class FetchResult:
    """Transport-level result of one fetch attempt."""

    ok: bool
    fetcher: str
    url: str
    html: str = ""
    markdown: str = ""
    text: str = ""
    http_status: Optional[int] = None
    latency_ms: float = 0.0
    error: Optional[str] = None
    extras: dict[str, Any] = field(default_factory=dict)

    def has_body(self) -> bool:
        """True when any content field is non-empty."""
        return bool(self.html.strip() or self.markdown.strip() or self.text.strip())


class BaseCrawler(ABC):
    """Shared crawler contract used by Firecrawl and Selenium adapters."""

    name: str = "base"

    @abstractmethod
    def fetch(self, url: str) -> FetchResult:
        """Retrieve `url`. Never raises for expected source failures — set ok=False."""
