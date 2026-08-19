"""
Job listing domain model.

Gemini produces a loosely typed dict. After schema + business validation the
pipeline stores a `JobListing`. The original Gemini dict is kept on
`gemini_object` so the Streamlit UI can print the extraction *as-is*.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class Salary(BaseModel):
    """Optional salary band extracted from listing text."""

    min: Optional[float] = None
    max: Optional[float] = None
    currency: Optional[str] = None


class JobListing(BaseModel):
    """
    A single validated job listing held in process memory.

    `id` is a stable hash of source + canonical URL (see processors.deduplicator)
    so repeated ingests of the same posting do not create duplicates.
    """

    id: str
    title: str
    company: str
    source_url: str
    location: Optional[str] = None
    salary: Optional[Salary] = None
    posted_at: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    crawl_id: Optional[str] = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Exact JSON object returned/parsed from Gemini — shown in the UI as-is.
    gemini_object: dict[str, Any] = Field(default_factory=dict)

    def as_display_dict(self) -> dict[str, Any]:
        """
        Return the Gemini object when present, otherwise the validated model.

        The Streamlit page uses this so reviewers see the extraction payload
        rather than an internal ORM-style dump.
        """
        if self.gemini_object:
            # Attach the in-memory id so the delete button can target it.
            payload = dict(self.gemini_object)
            payload["_memory_id"] = self.id
            return payload
        return self.model_dump(mode="json")
