"""In-memory repositories for jobs and crawl records."""

from app.repositories.crawl_repository import CrawlRepository, crawl_repository
from app.repositories.job_repository import JobRepository, job_repository

__all__ = [
    "CrawlRepository",
    "JobRepository",
    "crawl_repository",
    "job_repository",
]
