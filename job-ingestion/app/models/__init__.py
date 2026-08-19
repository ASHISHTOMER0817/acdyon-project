"""Domain models for job listings and crawl runs."""

from app.models.crawl import CrawlRecord
from app.models.job import JobListing, Salary

__all__ = ["CrawlRecord", "JobListing", "Salary"]
