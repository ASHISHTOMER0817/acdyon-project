"""
Load a few fixture job objects into process memory.

Useful for UI layout checks without calling Gemini. Does not replace a live
ingest — objects are synthetic and labelled as such.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.processors.normalizer import Normalizer
from app.repositories.job_repository import job_repository

FIXTURES = [
    {
        "title": "Senior Backend Engineer",
        "company": "Example Labs",
        "source_url": "https://example.com/jobs/backend-1",
        "location": "Remote",
        "salary": {"min": 120000, "max": 160000, "currency": "USD"},
        "posted_at": "2026-08-01",
        "description": "Build ingestion pipelines. Fixture only — not a real listing.",
        "source": "fixture",
    },
    {
        "title": "Data Engineer",
        "company": "Acme Analytics",
        "source_url": "https://example.com/jobs/data-2",
        "location": "Bengaluru",
        "salary": {"min": 1800000, "max": 2500000, "currency": "INR"},
        "posted_at": "2026-08-10",
        "description": "Warehouse + quality checks. Fixture only.",
        "source": "fixture",
    },
]


def seed() -> int:
    """Insert fixture Gemini-shaped objects into the in-memory repository."""
    normalizer = Normalizer()
    for obj in FIXTURES:
        job = normalizer.to_job(obj, source_name="fixture", page_url=obj["source_url"])
        job_repository.save(job)
    return job_repository.count()


if __name__ == "__main__":
    count = seed()
    print(f"Seeded {count} object(s) into in-memory job_repository (this process only).")
    print("Run this from the Streamlit process (sidebar) or import seed() in tests.")
