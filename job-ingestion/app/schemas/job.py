"""
API / UI schemas for job listings.

Kept separate from the domain model so the HTTP layer can evolve without
changing in-memory storage.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SalarySchema(BaseModel):
    """Salary band as exposed over the API."""

    min: Optional[float] = None
    max: Optional[float] = None
    currency: Optional[str] = None


class JobSchema(BaseModel):
    """Validated job listing as returned by GET /jobs."""

    id: str
    title: str
    company: str
    source_url: str
    location: Optional[str] = None
    salary: Optional[SalarySchema] = None
    posted_at: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    crawl_id: Optional[str] = None
    fetched_at: datetime
    gemini_object: dict[str, Any] = Field(default_factory=dict)


class JobExtractSchema(BaseModel):
    """
    Shape Gemini is instructed to return for each listing.

    Required: title, company, source_url.
    Everything else is optional and may be null.
    """

    title: str
    company: str
    source_url: str
    location: Optional[str] = None
    salary: Optional[SalarySchema] = None
    posted_at: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None


class GeminiExtractionEnvelope(BaseModel):
    """Top-level JSON envelope requested from Gemini."""

    jobs: list[JobExtractSchema] = Field(default_factory=list)
    notes: Optional[str] = None
