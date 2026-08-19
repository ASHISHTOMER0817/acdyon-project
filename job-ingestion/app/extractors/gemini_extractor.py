"""Gemini-backed extractor used by ExtractionService."""

from __future__ import annotations

from typing import Any, Optional

from app.clients.gemini import GeminiClient, GeminiError
from app.config.logging import get_logger
from app.config.settings import Settings, get_settings
from app.extractors.base import BaseExtractor

logger = get_logger(__name__)


class GeminiExtractor(BaseExtractor):
    """
    Sends preprocessed crawl text to Gemini and returns the raw objects.

    Callers persist those objects in memory immediately after validation.
    """

    name = "gemini"

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[GeminiClient] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or GeminiClient(self.settings)

    def extract(self, content: str, page_url: str, source_name: str) -> list[dict[str, Any]]:
        """Raise GeminiError if the model is missing or returns unusable JSON."""
        if not content.strip():
            logger.warning("Skipping Gemini: empty content for %s", page_url)
            return []
        try:
            return self.client.extract_jobs(
                content=content,
                page_url=page_url,
                source_name=source_name,
            )
        except GeminiError:
            raise
