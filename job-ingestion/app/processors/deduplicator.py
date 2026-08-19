"""
Canonical job identity and in-memory duplicate checks.

Primary key: hash(source + canonical_url)
Secondary fingerprint: hash(company + title + location) when URLs are unstable.
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


class Deduplicator:
    """Assign stable ids and drop objects already sitting in memory."""

    def canonical_url(self, url: str) -> str:
        """Lowercase host, drop fragments and common tracking query params."""
        if not url:
            return ""
        parsed = urlparse(url.strip())
        query = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}
        ]
        clean = parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower(),
            fragment="",
            query=urlencode(query),
        )
        return urlunparse(clean).rstrip("/")

    def job_id(self, source: str, source_url: str, title: str = "", company: str = "", location: str = "") -> str:
        """
        Primary identity: source + canonical URL.

        If the URL is missing, fall back to the attribute fingerprint so we
        still have a stable key for the in-memory dict.
        """
        canonical = self.canonical_url(source_url)
        if canonical:
            material = f"{source}|{canonical}"
        else:
            material = self.fingerprint(title, company, location)
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]

    def fingerprint(self, title: str, company: str, location: str) -> str:
        """Secondary identity when listing URLs are unstable."""
        blob = "|".join(
            part.strip().lower()
            for part in (company or "", title or "", location or "")
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def drop_known(self, objects: Iterable[dict[str, Any]], known_ids: set[str], source: str) -> tuple[list[dict[str, Any]], int]:
        """
        Filter Gemini objects that already exist in the job repository.

        Returns (new_objects, duplicate_count). Duplicate count is recorded
        by HealthService so a 100% duplicate run is visible, not silent.
        """
        fresh: list[dict[str, Any]] = []
        duplicates = 0
        for obj in objects:
            job_id = self.job_id(
                source=source or str(obj.get("source") or ""),
                source_url=str(obj.get("source_url") or ""),
                title=str(obj.get("title") or ""),
                company=str(obj.get("company") or ""),
                location=str(obj.get("location") or ""),
            )
            obj["_memory_id"] = job_id
            if job_id in known_ids:
                duplicates += 1
                continue
            known_ids.add(job_id)
            fresh.append(obj)
        return fresh, duplicates
