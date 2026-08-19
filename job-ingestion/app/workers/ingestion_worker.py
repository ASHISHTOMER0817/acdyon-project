"""
Ingestion worker.

The demo is on-demand (Streamlit button / Flask POST). This worker is the
same pipeline invoked from a CLI or a simple loop — not a stealth crawler.
"""

from __future__ import annotations

from typing import Optional

from app.config.logging import get_logger
from app.config.settings import Settings, get_settings
from app.services.ingestion_service import IngestionService, IngestReport

logger = get_logger(__name__)


class IngestionWorker:
    """Thin callable wrapper around IngestionService."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        service: Optional[IngestionService] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.service = service or IngestionService(self.settings)

    def run_once(self, url: Optional[str] = None, source_name: Optional[str] = None) -> IngestReport:
        """Run a single ingest against `url` or the configured default source."""
        target = url or self.settings.default_source_url
        logger.info("Worker ingest starting url=%s", target)
        report = self.service.ingest(target, source_name=source_name)
        logger.info("Worker ingest finished ok=%s %s", report.ok, report.message)
        return report
