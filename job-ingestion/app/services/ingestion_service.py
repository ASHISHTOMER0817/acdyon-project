"""
End-to-end ingestion orchestrator.

Flow:
    Firecrawl (or public HTTP) → validate content
        on failure/anomaly → Selenium
    persist raw crawl
    clean → Gemini extract → validate each object
    save valid objects to in-memory JobRepository
    update health counters

Never escalates request volume after a 429. Persistent failure marks the
source degraded/down instead of looping.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from app.clients.gemini import GeminiError
from app.config.logging import get_logger
from app.config.settings import Settings, get_settings
from app.crawlers.base import FetchResult
from app.crawlers.firecrawl_crawler import FirecrawlCrawler
from app.crawlers.selenium_crawler import SeleniumCrawler
from app.extractors.gemini_extractor import GeminiExtractor
from app.models.job import JobListing
from app.processors.cleaner import ContentCleaner
from app.processors.deduplicator import Deduplicator
from app.processors.normalizer import Normalizer
from app.repositories.crawl_repository import CrawlRepository, crawl_repository
from app.repositories.job_repository import JobRepository, job_repository
from app.services.extraction_service import ExtractionService
from app.services.health_service import HealthService, health_service
from app.validators.crawl_validator import CrawlValidator
from app.validators.job_validator import JobValidator

logger = get_logger(__name__)


@dataclass
class IngestReport:
    """Summary returned to Streamlit / Flask after one ingest."""

    ok: bool
    message: str
    source_url: str
    fetcher_used: Optional[str] = None
    crawl_id: Optional[str] = None
    jobs: list[JobListing] = field(default_factory=list)
    gemini_objects: list[dict[str, Any]] = field(default_factory=list)
    extracted: int = 0
    inserted: int = 0
    duplicates: int = 0
    invalid: int = 0
    health: dict[str, Any] = field(default_factory=dict)


class IngestionService:
    """Single entry point used by the UI, Flask, and CLI worker."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        primary: Optional[FirecrawlCrawler] = None,
        fallback: Optional[SeleniumCrawler] = None,
        extractor: Optional[GeminiExtractor] = None,
        jobs: Optional[JobRepository] = None,
        crawls: Optional[CrawlRepository] = None,
        health: Optional[HealthService] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.primary = primary or FirecrawlCrawler(self.settings)
        self.fallback = fallback or SeleniumCrawler(self.settings)
        self.extractor = extractor or GeminiExtractor(self.settings)
        self.jobs = jobs or job_repository
        self.crawls = crawls or crawl_repository
        self.health = health or health_service
        self.cleaner = ContentCleaner()
        self.deduplicator = Deduplicator()
        self.normalizer = Normalizer(self.deduplicator)
        self.job_validator = JobValidator()
        self.crawl_validator = CrawlValidator()
        self.extraction = ExtractionService(
            extractor=self.extractor,
            cleaner=self.cleaner,
            crawls=self.crawls,
        )
        self._last_request_at: float = 0.0

    def ingest(self, url: str, source_name: Optional[str] = None) -> IngestReport:
        """
        Fetch, extract, validate, and store jobs for `url`.

        `source_name` labels listings (default from settings).
        """
        source = source_name or self.settings.default_source_name
        self._pace()

        # Circuit: stop hitting a source that has failed repeatedly.
        if self.health.consecutive_failures >= self.settings.circuit_failure_threshold:
            msg = (
                f"Circuit open after {self.health.consecutive_failures} failures. "
                "Wait for cooldown or reset health before retrying."
            )
            logger.warning(msg)
            self.health.mark_degraded(msg)
            return IngestReport(ok=False, message=msg, source_url=url, health=self.health.snapshot())

        fetch, eval_result = self._fetch_with_fallback(url)
        crawl_id = uuid.uuid4().hex[:12]
        record = self.crawl_validator.to_record(crawl_id, fetch, eval_result)
        self.crawls.save(record)

        if not eval_result.ok or not fetch.has_body():
            message = eval_result.reason or fetch.error or "Fetch produced no usable content"
            self.health.record_ingest_failure(message)
            return IngestReport(
                ok=False,
                message=message,
                source_url=url,
                fetcher_used=fetch.fetcher,
                crawl_id=crawl_id,
                health=self.health.snapshot(),
            )

        try:
            raw_objects = self.extraction.extract_from_crawl(record, source)
        except GeminiError as exc:
            self.health.record_llm_failure(str(exc))
            return IngestReport(
                ok=False,
                message=f"Gemini extraction failed: {exc}",
                source_url=url,
                fetcher_used=fetch.fetcher,
                crawl_id=crawl_id,
                health=self.health.snapshot(),
            )

        extracted = len(raw_objects)
        known = self.jobs.known_ids()
        fresh, duplicate_count = self.deduplicator.drop_known(raw_objects, known, source)

        saved: list[JobListing] = []
        invalid = 0
        accepted_objects: list[dict[str, Any]] = []

        for obj in fresh:
            validation = self.job_validator.validate(obj, fallback_url=url)
            if not validation.ok or not validation.data:
                invalid += 1
                logger.info("Rejected Gemini object: %s", validation.errors)
                continue
            # Keep Gemini's original keys plus any fill-ins from validation.
            merged = dict(obj)
            merged.update({k: v for k, v in validation.data.items() if v is not None})
            job = self.normalizer.to_job(
                merged,
                source_name=source,
                crawl_id=crawl_id,
                page_url=url,
            )
            self.jobs.save(job)
            saved.append(job)
            accepted_objects.append(job.as_display_dict())

        self.health.record_extraction(
            extracted=extracted,
            inserted=len(saved),
            duplicates=duplicate_count,
            invalid=invalid,
        )
        if not saved and extracted == 0:
            self.health.record_ingest_failure("Gemini returned zero jobs")
            self.health.mark_degraded("Gemini returned zero jobs")

        ok = len(saved) > 0 or duplicate_count > 0
        message = (
            f"Inserted {len(saved)} job(s); {duplicate_count} duplicate(s); "
            f"{invalid} invalid; {extracted} extracted via Gemini"
        )
        logger.info(message)
        return IngestReport(
            ok=ok,
            message=message,
            source_url=url,
            fetcher_used=fetch.fetcher,
            crawl_id=crawl_id,
            jobs=saved,
            gemini_objects=accepted_objects,
            extracted=extracted,
            inserted=len(saved),
            duplicates=duplicate_count,
            invalid=invalid,
            health=self.health.snapshot(),
        )

    def delete_job(self, job_id: str) -> bool:
        """Remove one listing from process memory (Streamlit ✕ / DELETE)."""
        return self.jobs.delete(job_id)

    def list_jobs(self) -> list[JobListing]:
        """All listings currently held in memory."""
        return self.jobs.list_all()

    def _pace(self) -> None:
        """Minimum interval between outbound requests (even on public APIs)."""
        gap = self.settings.min_request_interval_seconds
        now = time.monotonic()
        wait = gap - (now - self._last_request_at)
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    def _fetch_with_fallback(self, url: str) -> tuple[FetchResult, Any]:
        """Primary fetch, then Selenium if transport or content checks fail."""
        primary = self.primary.fetch(url)
        self.health.record_fetch(
            ok=primary.ok,
            http_status=primary.http_status,
            latency_ms=primary.latency_ms,
            fetcher=primary.fetcher,
        )
        evaluation = self.crawl_validator.evaluate(primary)
        if evaluation.ok:
            return primary, evaluation

        if evaluation.anomaly:
            self.health.record_anomaly()

        logger.info("Primary fetch unusable (%s); invoking Selenium fallback", evaluation.reason)
        self.health.record_fallback()
        self._pace()
        secondary = self.fallback.fetch(url)
        self.health.record_fetch(
            ok=secondary.ok,
            http_status=secondary.http_status,
            latency_ms=secondary.latency_ms,
            fetcher=secondary.fetcher,
        )
        secondary_eval = self.crawl_validator.evaluate(secondary)
        if secondary_eval.anomaly:
            self.health.record_anomaly()
        # Prefer whichever result actually has a body.
        if secondary_eval.ok:
            return secondary, secondary_eval
        if primary.has_body() and not secondary.has_body():
            return primary, evaluation
        return secondary, secondary_eval
