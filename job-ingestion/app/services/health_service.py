"""
Process-wide health / observability counters.

Distinguishes "fetcher returned HTTP 200" from "ingestion produced valid jobs".
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Optional


class HealthService:
    """Mutable metrics bag shared by the pipeline and the Streamlit sidebar."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset_unlocked()

    def _reset_unlocked(self) -> None:
        self.last_successful_ingestion: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.source_status: str = "unknown"  # healthy | degraded | down | unknown
        self.fetch_attempts: int = 0
        self.fetch_successes: int = 0
        self.fetch_failures: int = 0
        self.http_429_count: int = 0
        self.fallback_count: int = 0
        self.pages_processed: int = 0
        self.listings_extracted: int = 0
        self.listings_inserted: int = 0
        self.duplicates: int = 0
        self.schema_validation_failures: int = 0
        self.llm_extraction_failures: int = 0
        self.parse_anomalies: int = 0
        self.consecutive_failures: int = 0
        self.last_latency_ms: float = 0.0
        self.last_fetcher: Optional[str] = None

    def reset(self) -> None:
        """Zero counters (demo helper)."""
        with self._lock:
            self._reset_unlocked()

    def record_fetch(self, *, ok: bool, http_status: Optional[int], latency_ms: float, fetcher: str) -> None:
        """Record one fetch attempt."""
        with self._lock:
            self.fetch_attempts += 1
            self.last_latency_ms = latency_ms
            self.last_fetcher = fetcher
            if http_status == 429:
                self.http_429_count += 1
            if ok:
                self.fetch_successes += 1
            else:
                self.fetch_failures += 1

    def record_fallback(self) -> None:
        """Selenium (or secondary fetcher) was invoked."""
        with self._lock:
            self.fallback_count += 1

    def record_anomaly(self) -> None:
        """Content-level anomaly (empty body, no markers, unexpected drop)."""
        with self._lock:
            self.parse_anomalies += 1

    def record_extraction(self, extracted: int, inserted: int, duplicates: int, invalid: int) -> None:
        """Record Gemini + validation outcomes for one ingest."""
        with self._lock:
            self.pages_processed += 1
            self.listings_extracted += extracted
            self.listings_inserted += inserted
            self.duplicates += duplicates
            self.schema_validation_failures += invalid
            if inserted > 0:
                self.last_successful_ingestion = datetime.now(timezone.utc)
                self.consecutive_failures = 0
                self.source_status = "healthy"
                self.last_error = None

    def record_llm_failure(self, message: str) -> None:
        """Gemini failed to produce usable JSON."""
        with self._lock:
            self.llm_extraction_failures += 1
            self.last_error = message
            self.consecutive_failures += 1
            self._update_status_unlocked()

    def record_ingest_failure(self, message: str) -> None:
        """Whole ingest failed (both fetchers down, etc.)."""
        with self._lock:
            self.last_error = message
            self.consecutive_failures += 1
            self._update_status_unlocked()

    def mark_degraded(self, message: str) -> None:
        """Source is serving something, but not a clean ingest."""
        with self._lock:
            self.source_status = "degraded"
            self.last_error = message

    def _update_status_unlocked(self) -> None:
        if self.consecutive_failures >= 3:
            self.source_status = "down"
        elif self.consecutive_failures > 0:
            self.source_status = "degraded"

    def snapshot(self) -> dict[str, Any]:
        """JSON-serialisable health view for UI and GET /health."""
        with self._lock:
            last = self.last_successful_ingestion
            return {
                "source_status": self.source_status,
                "last_successful_ingestion": last.isoformat() if last else None,
                "last_error": self.last_error,
                "last_fetcher": self.last_fetcher,
                "fetch_attempts": self.fetch_attempts,
                "fetch_successes": self.fetch_successes,
                "fetch_failures": self.fetch_failures,
                "http_429_count": self.http_429_count,
                "fallback_count": self.fallback_count,
                "pages_processed": self.pages_processed,
                "listings_extracted": self.listings_extracted,
                "listings_inserted": self.listings_inserted,
                "duplicates": self.duplicates,
                "schema_validation_failures": self.schema_validation_failures,
                "llm_extraction_failures": self.llm_extraction_failures,
                "parse_anomalies": self.parse_anomalies,
                "consecutive_failures": self.consecutive_failures,
                "last_latency_ms": round(self.last_latency_ms, 1),
            }


health_service = HealthService()
