"""Pydantic request/response schemas for the Flask API and Streamlit."""

from app.schemas.crawl import CrawlIngestRequest, CrawlRecordSchema
from app.schemas.job import JobSchema, SalarySchema

__all__ = ["CrawlIngestRequest", "CrawlRecordSchema", "JobSchema", "SalarySchema"]
