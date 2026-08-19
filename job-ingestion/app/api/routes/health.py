"""Health / observability endpoint."""

from __future__ import annotations

from flask import Blueprint, jsonify

from app.repositories.job_repository import job_repository
from app.services.health_service import health_service

health_bp = Blueprint("health", __name__)


@health_bp.get("")
def health():
    """
    Pipeline metrics.

    Distinguishes fetch HTTP success from 'we actually stored valid jobs'.
    """
    snapshot = health_service.snapshot()
    snapshot["jobs_in_memory"] = job_repository.count()
    http_status = 200
    if snapshot["source_status"] == "down":
        http_status = 503
    elif snapshot["source_status"] == "degraded":
        http_status = 200
    return jsonify(snapshot), http_status
