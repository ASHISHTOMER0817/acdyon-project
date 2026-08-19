"""Optional background / CLI worker that triggers ingestion."""

from app.workers.ingestion_worker import IngestionWorker

__all__ = ["IngestionWorker"]
