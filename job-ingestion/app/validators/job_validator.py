"""
Schema + business validation for Gemini job objects.

Invalid objects are rejected, not silently stored. Title, company, and
source_url are required by the design.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from pydantic import ValidationError

from app.schemas.job import JobExtractSchema


@dataclass
class JobValidationResult:
    """Outcome of validating one Gemini object."""

    ok: bool
    errors: list[str]
    data: Optional[dict[str, Any]] = None


class JobValidator:
    """Pydantic schema check plus a few business rules."""

    def validate(self, obj: dict[str, Any], fallback_url: str = "") -> JobValidationResult:
        """
        Validate one Gemini job dict.

        If source_url is missing, `fallback_url` (the crawled page) is filled
        in *before* schema validation so a listing on a board index still
        has a required URL.
        """
        candidate = dict(obj)
        if not str(candidate.get("source_url") or "").strip() and fallback_url:
            candidate["source_url"] = fallback_url

        try:
            parsed = JobExtractSchema.model_validate(candidate)
        except ValidationError as exc:
            messages = [err["msg"] for err in exc.errors()]
            return JobValidationResult(ok=False, errors=messages)

        errors: list[str] = []
        if not parsed.title.strip():
            errors.append("title is blank")
        if not parsed.company.strip():
            errors.append("company is blank")
        if not str(parsed.source_url).strip():
            errors.append("source_url is blank")
        if parsed.salary and parsed.salary.min is not None and parsed.salary.max is not None:
            if parsed.salary.min > parsed.salary.max:
                errors.append("salary.min is greater than salary.max")

        if errors:
            return JobValidationResult(ok=False, errors=errors)

        return JobValidationResult(ok=True, errors=[], data=parsed.model_dump())
