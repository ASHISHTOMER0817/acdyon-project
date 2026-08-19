"""Turn a validated Gemini dict into a JobListing domain object."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.models.job import JobListing, Salary
from app.processors.deduplicator import Deduplicator


class Normalizer:
    """Map loosely typed extraction output onto the domain model."""

    def __init__(self, deduplicator: Optional[Deduplicator] = None) -> None:
        self.deduplicator = deduplicator or Deduplicator()

    def to_job(
        self,
        gemini_object: dict[str, Any],
        *,
        source_name: str,
        crawl_id: Optional[str] = None,
        page_url: str = "",
    ) -> JobListing:
        """
        Build a JobListing, preserving the original Gemini object.

        `gemini_object` is stored untouched (aside from the internal
        `_memory_id` used by the UI delete button).
        """
        source_url = str(gemini_object.get("source_url") or page_url)
        source = str(gemini_object.get("source") or source_name)
        title = str(gemini_object.get("title") or "").strip()
        company = str(gemini_object.get("company") or "").strip()
        location = self._optional_str(gemini_object.get("location"))

        job_id = gemini_object.get("_memory_id") or self.deduplicator.job_id(
            source=source,
            source_url=source_url,
            title=title,
            company=company,
            location=location or "",
        )

        salary = self._salary(gemini_object.get("salary"))
        # Copy so later UI edits cannot mutate the stored extraction payload.
        preserved = {k: v for k, v in gemini_object.items() if k != "_memory_id"}

        return JobListing(
            id=str(job_id),
            title=title,
            company=company,
            source_url=self.deduplicator.canonical_url(source_url) or source_url,
            location=location,
            salary=salary,
            posted_at=self._optional_str(gemini_object.get("posted_at")),
            description=self._optional_str(gemini_object.get("description")),
            source=source,
            crawl_id=crawl_id,
            fetched_at=datetime.now(timezone.utc),
            gemini_object=preserved,
        )

    @staticmethod
    def _optional_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _salary(value: Any) -> Optional[Salary]:
        if not isinstance(value, dict):
            return None
        return Salary(
            min=_to_float(value.get("min")),
            max=_to_float(value.get("max")),
            currency=(str(value["currency"]).strip() if value.get("currency") else None),
        )


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
