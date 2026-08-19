"""Job listing HTTP routes (in-memory store)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.ingestion_service import IngestionService

jobs_bp = Blueprint("jobs", __name__)
_service = IngestionService()


@jobs_bp.get("")
def list_jobs():
    """Return every job currently held in process memory."""
    jobs = _service.list_jobs()
    return jsonify(
        {
            "count": len(jobs),
            "jobs": [job.as_display_dict() for job in jobs],
        }
    )


@jobs_bp.post("/ingest")
def ingest():
    """
    Fetch a public URL, run Gemini extraction, store valid objects.

    JSON body: {"url": "...", "source_name": "optional"}
    """
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()
    if not url:
        return jsonify({"ok": False, "error": "url is required"}), 400
    source_name = payload.get("source_name")
    report = _service.ingest(url, source_name=source_name)
    status = 200 if report.ok else 502
    return jsonify(
        {
            "ok": report.ok,
            "message": report.message,
            "source_url": report.source_url,
            "fetcher_used": report.fetcher_used,
            "crawl_id": report.crawl_id,
            "extracted": report.extracted,
            "inserted": report.inserted,
            "duplicates": report.duplicates,
            "invalid": report.invalid,
            "jobs": report.gemini_objects,
            "health": report.health,
        }
    ), status


@jobs_bp.delete("/<job_id>")
def delete_job(job_id: str):
    """Remove one Gemini object from memory."""
    deleted = _service.delete_job(job_id)
    if not deleted:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({"ok": True, "deleted": job_id})


@jobs_bp.post("/clear")
def clear_jobs():
    """Drop all in-memory jobs (demo helper)."""
    _service.jobs.clear()
    return jsonify({"ok": True, "count": 0})
