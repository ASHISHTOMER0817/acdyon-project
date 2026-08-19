"""
Streamlit demo UI.

Run from the `job-ingestion/` directory:

    .venv\\Scripts\\streamlit run streamlit_app.py

The page:
1. Triggers ingest against a public URL (Firecrawl → Selenium fallback → Gemini).
2. Saves each validated Gemini object in process memory.
3. Prints those objects as-is.
4. Offers an ✕ button on every object to delete it from memory.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow `import app` when launched via `streamlit run streamlit_app.py`.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.config.logging import configure_logging  # noqa: E402
from app.config.settings import get_settings  # noqa: E402
from app.repositories.job_repository import job_repository  # noqa: E402
from app.services.health_service import health_service  # noqa: E402
from app.services.ingestion_service import IngestionService  # noqa: E402

configure_logging()
st.set_page_config(page_title="Job ingestion", page_icon="🗂️", layout="wide")


@st.cache_resource
def get_service() -> IngestionService:
    """One IngestionService per Streamlit process (shares in-memory repos)."""
    return IngestionService()


def _render_health(snapshot: dict) -> None:
    """Sidebar metrics — last ingest, counts, source status."""
    st.sidebar.subheader("Pipeline health")
    status = snapshot.get("source_status", "unknown")
    st.sidebar.metric("Source", status)
    st.sidebar.metric("Jobs in memory", job_repository.count())
    st.sidebar.metric("Inserted (session)", snapshot.get("listings_inserted", 0))
    st.sidebar.metric("Duplicates", snapshot.get("duplicates", 0))
    st.sidebar.metric("HTTP 429s", snapshot.get("http_429_count", 0))
    st.sidebar.metric("Fallbacks", snapshot.get("fallback_count", 0))
    st.sidebar.metric("Invalid (schema)", snapshot.get("schema_validation_failures", 0))
    st.sidebar.caption(
        f"Last success: {snapshot.get('last_successful_ingestion') or '—'}  \n"
        f"Last fetcher: {snapshot.get('last_fetcher') or '—'}  \n"
        f"Last error: {snapshot.get('last_error') or '—'}"
    )


def main() -> None:
    """Render the ingest form and the in-memory object list."""
    settings = get_settings()
    service = get_service()

    st.title("Job listing ingestion")
    st.write(
        "Public-source demo: fetch → optional Selenium fallback → **Gemini** "
        "structured objects → store in **runtime memory**. Click ✕ to drop an object."
    )

    if not settings.gemini_configured:
        st.error(
            "GEMINI_API_KEY is not set. Copy `.env.example` to `.env` and add a key. "
            "Gemini is required to generate the job objects."
        )

    col_url, col_source = st.columns([3, 1])
    with col_url:
        url = st.text_input(
            "Public job source URL",
            value=settings.default_source_url,
            help="Use a public JSON/RSS/API or a sandbox you control. Not LinkedIn.",
        )
    with col_source:
        source_name = st.text_input("Source name", value=settings.default_source_name)

    run_col, clear_col = st.columns([1, 1])
    with run_col:
        ingest_clicked = st.button("Run ingest", type="primary", use_container_width=True)
    with clear_col:
        clear_clicked = st.button("Clear all objects", use_container_width=True)

    if clear_clicked:
        job_repository.clear()
        st.success("In-memory store cleared.")
        st.rerun()

    if ingest_clicked:
        if not url.strip():
            st.warning("Enter a URL.")
        elif not settings.gemini_configured:
            st.stop()
        else:
            with st.spinner("Fetching and extracting with Gemini…"):
                report = service.ingest(url.strip(), source_name=source_name.strip() or None)
            if report.ok:
                st.success(report.message)
            else:
                st.error(report.message)
            st.caption(
                f"fetcher={report.fetcher_used}  crawl_id={report.crawl_id}  "
                f"extracted={report.extracted} inserted={report.inserted} "
                f"dupes={report.duplicates} invalid={report.invalid}"
            )
            # Rerun so the job list below renders immediately after ingest.
            st.rerun()

    _render_health(health_service.snapshot())

    jobs = service.list_jobs()
    st.subheader(f"Objects in memory ({len(jobs)})")
    if not jobs:
        st.info("No objects yet. Run ingest to generate Gemini job objects.")
        return

    for job in jobs:
        header_left, header_right = st.columns([0.92, 0.08])
        label = f"{job.title} — {job.company}"
        with header_left:
            st.markdown(f"**{label}**")
            st.caption(job.id)
        with header_right:
            # Unique key per job so Streamlit does not collide buttons.
            if st.button("✕", key=f"delete-{job.id}", help="Delete this object from memory"):
                service.delete_job(job.id)
                st.rerun()
        # Print the Gemini object as-is (plus _memory_id for traceability).
        st.json(job.as_display_dict())
        with st.expander("Raw JSON text"):
            st.code(json.dumps(job.as_display_dict(), indent=2, default=str), language="json")
        st.divider()


# Streamlit executes this file on every rerun.
main()
