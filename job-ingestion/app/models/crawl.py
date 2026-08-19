"""
Crawl-run domain model.

Raw HTML/Markdown is stored *before* Gemini extraction so a prompt or model
change can be re-run without hitting the source again.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class CrawlRecord(BaseModel):
    """One fetch attempt (Firecrawl or Selenium) and its raw payload."""

    id: str
    source_url: str
    fetcher: str  # "firecrawl" | "selenium" | "http"
    status: str  # "success" | "failure" | "anomaly" | "degraded"
    http_status: Optional[int] = None
    raw_html: Optional[str] = None
    raw_markdown: Optional[str] = None
    raw_text: Optional[str] = None
    content_length: int = 0
    listings_hint: int = 0  # crude count before LLM extraction
    anomaly: bool = False
    anomaly_reason: Optional[str] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def has_content(self) -> bool:
        """True when at least one raw payload field is non-empty."""
        return bool(
            (self.raw_html and self.raw_html.strip())
            or (self.raw_markdown and self.raw_markdown.strip())
            or (self.raw_text and self.raw_text.strip())
        )

    def combined_text(self) -> str:
        """Prefer markdown, then text, then HTML, for the Gemini prompt."""
        for candidate in (self.raw_markdown, self.raw_text, self.raw_html):
            if candidate and candidate.strip():
                return candidate
        return ""
