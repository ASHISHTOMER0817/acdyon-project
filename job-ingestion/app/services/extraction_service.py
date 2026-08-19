"""Run Gemini extraction against already-stored raw crawl text."""

from __future__ import annotations

from typing import Any, Optional

from app.clients.gemini import GeminiError
from app.config.logging import get_logger
from app.extractors.gemini_extractor import GeminiExtractor
from app.models.crawl import CrawlRecord
from app.processors.cleaner import ContentCleaner
from app.repositories.crawl_repository import CrawlRepository, crawl_repository

logger = get_logger(__name__)


class ExtractionService:
    """
    Isolated extraction step.

    Lets us re-run Gemini on a saved CrawlRecord without fetching again
    (prompt or model changes).
    """

    def __init__(
        self,
        extractor: Optional[GeminiExtractor] = None,
        cleaner: Optional[ContentCleaner] = None,
        crawls: Optional[CrawlRepository] = None,
    ) -> None:
        self.extractor = extractor or GeminiExtractor()
        self.cleaner = cleaner or ContentCleaner()
        self.crawls = crawls or crawl_repository

    def extract_from_crawl(self, crawl: CrawlRecord, source_name: str) -> list[dict[str, Any]]:
        """Clean crawl text and return raw Gemini job objects."""
        cleaned = self.cleaner.clean(crawl.combined_text())
        if not cleaned:
            logger.warning("Crawl %s has no text to extract", crawl.id)
            return []
        try:
            return self.extractor.extract(
                content=cleaned,
                page_url=crawl.source_url,
                source_name=source_name,
            )
        except GeminiError as exc:
            logger.error("Gemini extraction failed for crawl %s: %s", crawl.id, exc)
            raise

    def extract_from_crawl_id(self, crawl_id: str, source_name: str) -> list[dict[str, Any]]:
        """Look up a stored crawl and extract. Raises KeyError if missing."""
        crawl = self.crawls.get(crawl_id)
        if crawl is None:
            raise KeyError(f"Unknown crawl id: {crawl_id}")
        return self.extract_from_crawl(crawl, source_name)
