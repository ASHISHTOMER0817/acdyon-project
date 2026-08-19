"""
In-memory job store.

The assessment demo persists listings for the lifetime of the Python process
(Streamlit or Flask), not in PostgreSQL. After Gemini returns objects they are
saved here immediately. Deleting from the Streamlit ✕ button removes the
entry from this dict.
"""

from __future__ import annotations

import threading
from typing import Optional

from app.models.job import JobListing


class JobRepository:
    """Thread-safe dict of JobListing keyed by stable job id."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, JobListing] = {}

    def save(self, job: JobListing) -> JobListing:
        """Upsert a listing. Same id overwrites the previous object."""
        with self._lock:
            self._jobs[job.id] = job
            return job

    def save_many(self, jobs: list[JobListing]) -> list[JobListing]:
        """Upsert a batch of listings; returns the saved objects."""
        saved: list[JobListing] = []
        for job in jobs:
            saved.append(self.save(job))
        return saved

    def get(self, job_id: str) -> Optional[JobListing]:
        """Return one listing or None."""
        with self._lock:
            return self._jobs.get(job_id)

    def list_all(self) -> list[JobListing]:
        """Return listings newest-first (by fetched_at)."""
        with self._lock:
            jobs = list(self._jobs.values())
        jobs.sort(key=lambda j: j.fetched_at, reverse=True)
        return jobs

    def delete(self, job_id: str) -> bool:
        """
        Remove one listing.

        Returns True if it existed. Used by the Streamlit ✕ button and
        DELETE /jobs/<id>.
        """
        with self._lock:
            if job_id not in self._jobs:
                return False
            del self._jobs[job_id]
            return True

    def exists(self, job_id: str) -> bool:
        """True if this id is already in memory (used by the deduplicator)."""
        with self._lock:
            return job_id in self._jobs

    def known_ids(self) -> set[str]:
        """Snapshot of ids currently stored — used to skip LLM re-extraction."""
        with self._lock:
            return set(self._jobs.keys())

    def clear(self) -> None:
        """Drop every listing. Demo helper, not part of production ingest."""
        with self._lock:
            self._jobs.clear()

    def count(self) -> int:
        """Current number of listings in memory."""
        with self._lock:
            return len(self._jobs)


# Process-wide singleton so Streamlit reruns share the same list.
job_repository = JobRepository()
