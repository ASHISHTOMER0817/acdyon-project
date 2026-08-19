"""
Flask application factory.

The Streamlit UI talks to IngestionService directly in-process. This API is
the same memory store exposed as JSON for health checks and optional clients.
"""

from __future__ import annotations

from flask import Flask, jsonify
from flask_cors import CORS

from app.api.routes.health import health_bp
from app.api.routes.jobs import jobs_bp
from app.config.logging import configure_logging
from app.config.settings import get_settings


def create_app() -> Flask:
    """Build a Flask app with jobs + health blueprints."""
    configure_logging()
    settings = get_settings()
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    CORS(app)

    app.register_blueprint(jobs_bp, url_prefix="/jobs")
    app.register_blueprint(health_bp, url_prefix="/health")

    @app.get("/")
    def index():
        """Tiny index so a browser hit on :8000 is self-explanatory."""
        return jsonify(
            {
                "service": "job-ingestion",
                "docs": "See README.md",
                "endpoints": {
                    "GET /jobs": "List in-memory job objects",
                    "POST /jobs/ingest": "Fetch + Gemini extract + store",
                    "DELETE /jobs/<id>": "Remove one object from memory",
                    "GET /health": "Pipeline metrics",
                },
                "default_source": settings.default_source_url,
            }
        )

    return app


def main() -> None:
    """`python -m app.api.app` entrypoint."""
    settings = get_settings()
    application = create_app()
    print(
        f"Flask listening on {settings.flask_host}:{settings.flask_port}",
        flush=True,
    )
    application.run(host=settings.flask_host, port=settings.flask_port, debug=settings.flask_debug)


if __name__ == "__main__":
    main()
