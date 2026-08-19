"""Request/response schemas for crawl and ingest endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CrawlIngestRequest(BaseModel):
    """Body for POST /jobs/ingest."""

    url: str = Field(..., description="Public job-board URL or JSON/RSS endpoint")
    source_name: Optional[str] = Field(
        default=None,
        description="Short source label stored on each job, e.g. remoteok",
    )


class CrawlRecordSchema(BaseModel):
    """Public view of a crawl record (raw HTML omitted if huge)."""

    id: str
    source_url: str
    fetcher: str
    status: str
    http_status: Optional[int] = None
    content_length: int
    listings_hint: int
    anomaly: bool
    anomaly_reason: Optional[str] = None
    error: Optional[str] = None
    latency_ms: float
    fetched_at: datetime
