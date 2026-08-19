"""CLI: run one ingest against the default or provided URL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config.logging import configure_logging
from app.workers.ingestion_worker import IngestionWorker


def main() -> int:
    """Parse args, run ingest, print a JSON summary."""
    configure_logging()
    parser = argparse.ArgumentParser(description="Run a single job-listing ingest")
    parser.add_argument("--url", default=None, help="Public source URL")
    parser.add_argument("--source-name", default=None, help="Short source label")
    args = parser.parse_args()

    report = IngestionWorker().run_once(url=args.url, source_name=args.source_name)
    print(
        json.dumps(
            {
                "ok": report.ok,
                "message": report.message,
                "fetcher_used": report.fetcher_used,
                "inserted": report.inserted,
                "extracted": report.extracted,
                "duplicates": report.duplicates,
                "invalid": report.invalid,
                "jobs": report.gemini_objects,
            },
            indent=2,
            default=str,
        )
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
