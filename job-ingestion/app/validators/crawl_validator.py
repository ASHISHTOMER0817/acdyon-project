"""
Transport + content-level checks for a crawl.

HTTP 200 with an empty or tiny body is an anomaly, not a success. That is
what triggers Selenium fallback in IngestionService.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.crawlers.base import FetchResult
from app.models.crawl import CrawlRecord


@dataclass
class CrawlValidationResult:
    """Whether a fetch should be treated as usable content."""

    ok: bool
    anomaly: bool
    reason: Optional[str] = None


class CrawlValidator:
    """Decide success / failure / anomaly from a FetchResult."""

    min_content_bytes: int = 80
    # Very rough "this page looks like it has listings" markers.
    listing_markers = (
        "job",
        "hiring",
        "engineer",
        "salary",
        "remote",
        "full-time",
        "company",
        "position",
    )

    def evaluate(self, result: FetchResult) -> CrawlValidationResult:
        """
        Content-level success, independent of HTTP status.

        Anomalous results should not be marked as a successful ingest even
        if the fetcher returned 200.
        """
        if not result.ok:
            return CrawlValidationResult(ok=False, anomaly=False, reason=result.error or "fetch failed")
        if result.http_status == 429:
            return CrawlValidationResult(ok=False, anomaly=True, reason="HTTP 429")
        if result.http_status is not None and result.http_status >= 400:
            return CrawlValidationResult(
                ok=False,
                anomaly=False,
                reason=f"HTTP {result.http_status}",
            )
        if not result.has_body():
            return CrawlValidationResult(ok=False, anomaly=True, reason="empty body")

        blob = result.markdown or result.text or result.html or ""
        if len(blob.strip()) < self.min_content_bytes:
            return CrawlValidationResult(ok=False, anomaly=True, reason="response too small")

        lowered = blob.lower()
        marker_hits = sum(1 for marker in self.listing_markers if marker in lowered)
        if marker_hits == 0:
            return CrawlValidationResult(
                ok=False,
                anomaly=True,
                reason="no job-related content markers",
            )

        return CrawlValidationResult(ok=True, anomaly=False, reason=None)

    def hint_listing_count(self, text: str) -> int:
        """Crude pre-LLM count used only for anomaly dashboards, not storage."""
        if not text:
            return 0
        lowered = text.lower()
        return lowered.count('"title"') + lowered.count("<article") + lowered.count("job-listing")

    def to_record(
        self,
        crawl_id: str,
        result: FetchResult,
        evaluation: CrawlValidationResult,
    ) -> CrawlRecord:
        """Build the raw CrawlRecord stored before Gemini runs."""
        body = result.markdown or result.text or result.html or ""
        status = "success"
        if not evaluation.ok and evaluation.anomaly:
            status = "anomaly"
        elif not evaluation.ok:
            status = "failure"

        return CrawlRecord(
            id=crawl_id,
            source_url=result.url,
            fetcher=result.fetcher,
            status=status,
            http_status=result.http_status,
            raw_html=result.html or None,
            raw_markdown=result.markdown or None,
            raw_text=result.text or None,
            content_length=len(body),
            listings_hint=self.hint_listing_count(body),
            anomaly=evaluation.anomaly,
            anomaly_reason=evaluation.reason,
            error=result.error,
            latency_ms=result.latency_ms,
        )
