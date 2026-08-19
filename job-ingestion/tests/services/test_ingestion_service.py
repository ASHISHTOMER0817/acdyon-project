"""Ingestion service tests with fake crawlers and a fake Gemini extractor."""

from __future__ import annotations

from app.crawlers.base import BaseCrawler, FetchResult
from app.extractors.gemini_extractor import GeminiExtractor
from app.repositories.crawl_repository import CrawlRepository
from app.repositories.job_repository import JobRepository
from app.services.health_service import HealthService
from app.services.ingestion_service import IngestionService


class _OkCrawler(BaseCrawler):
    name = "http"

    def fetch(self, url: str) -> FetchResult:
        listing = (
            '{"title": "Platform Engineer", "company": "Globex", "job": true, '
            '"location": "Remote", "description": "Hiring a remote software engineer '
            'to build ingestion pipelines and data quality checks for the job board."}'
        )
        return FetchResult(
            ok=True,
            fetcher="http",
            url=url,
            markdown=listing,
            http_status=200,
            latency_ms=5,
        )


class _FailCrawler(BaseCrawler):
    name = "selenium"

    def fetch(self, url: str) -> FetchResult:
        return FetchResult(ok=False, fetcher="selenium", url=url, error="timeout")


class _FakeGemini:
    available = True

    def extract_jobs(self, content, page_url, source_name, max_jobs=None):
        return [
            {
                "title": "Platform Engineer",
                "company": "Globex",
                "source_url": f"{page_url}/role/1",
                "location": "Remote",
                "salary": {"min": 100000, "max": 140000, "currency": "USD"},
                "description": "Build pipelines",
                "source": source_name,
            }
        ]


def _service() -> IngestionService:
    jobs = JobRepository()
    crawls = CrawlRepository()
    health = HealthService()
    extractor = GeminiExtractor(client=_FakeGemini())
    return IngestionService(
        primary=_OkCrawler(),
        fallback=_FailCrawler(),
        extractor=extractor,
        jobs=jobs,
        crawls=crawls,
        health=health,
    )


def test_ingest_saves_gemini_object_in_memory():
    svc = _service()
    report = svc.ingest("https://example.com/jobs", source_name="example")
    assert report.ok
    assert report.inserted == 1
    stored = svc.list_jobs()
    assert len(stored) == 1
    assert stored[0].gemini_object["title"] == "Platform Engineer"


def test_delete_removes_object():
    svc = _service()
    svc.ingest("https://example.com/jobs", source_name="example")
    job_id = svc.list_jobs()[0].id
    assert svc.delete_job(job_id) is True
    assert svc.list_jobs() == []


def test_second_ingest_is_duplicate():
    svc = _service()
    svc.ingest("https://example.com/jobs", source_name="example")
    report = svc.ingest("https://example.com/jobs", source_name="example")
    assert report.duplicates == 1
    assert report.inserted == 0
    assert len(svc.list_jobs()) == 1
