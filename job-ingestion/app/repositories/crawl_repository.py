"""In-memory store for raw crawl records (pre-Gemini)."""

from __future__ import annotations

import threading
from typing import Optional

from app.models.crawl import CrawlRecord


class CrawlRepository:
    """Thread-safe list of crawl attempts for the current process."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._crawls: dict[str, CrawlRecord] = {}

    def save(self, crawl: CrawlRecord) -> CrawlRecord:
        """Persist a raw crawl so extraction can be re-run later."""
        with self._lock:
            self._crawls[crawl.id] = crawl
            return crawl

    def get(self, crawl_id: str) -> Optional[CrawlRecord]:
        """Return one crawl record or None."""
        with self._lock:
            return self._crawls.get(crawl_id)

    def list_all(self) -> list[CrawlRecord]:
        """Return crawls newest-first."""
        with self._lock:
            crawls = list(self._crawls.values())
        crawls.sort(key=lambda c: c.fetched_at, reverse=True)
        return crawls

    def latest(self) -> Optional[CrawlRecord]:
        """Most recent crawl, used by the health dashboard."""
        crawls = self.list_all()
        return crawls[0] if crawls else None

    def clear(self) -> None:
        """Drop all crawl records."""
        with self._lock:
            self._crawls.clear()

    def count(self) -> int:
        """Number of crawl attempts stored."""
        with self._lock:
            return len(self._crawls)


crawl_repository = CrawlRepository()
