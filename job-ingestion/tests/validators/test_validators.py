"""Schema and crawl validation tests."""

from app.crawlers.base import FetchResult
from app.validators.crawl_validator import CrawlValidator
from app.validators.job_validator import JobValidator


def test_job_requires_title_company_url():
    result = JobValidator().validate({"title": None, "company": "Acme"})
    assert result.ok is False


def test_job_fills_fallback_url():
    result = JobValidator().validate(
        {"title": "Dev", "company": "Acme"},
        fallback_url="https://example.com/jobs",
    )
    assert result.ok is True
    assert result.data["source_url"] == "https://example.com/jobs"


def test_empty_body_is_anomaly():
    fetch = FetchResult(ok=True, fetcher="http", url="https://x", html="", http_status=200)
    evaluation = CrawlValidator().evaluate(fetch)
    assert evaluation.ok is False
    assert evaluation.anomaly is True


def test_job_markers_pass():
    body = (
        "Hiring a remote software engineer. Company: Acme. "
        "Full-time job listing with salary, location, and a long description "
        "so the crawl is not treated as an empty or tiny response."
    )
    fetch = FetchResult(
        ok=True,
        fetcher="http",
        url="https://x",
        markdown=body,
        http_status=200,
    )
    evaluation = CrawlValidator().evaluate(fetch)
    assert evaluation.ok is True
