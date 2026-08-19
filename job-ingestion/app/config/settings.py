"""
Runtime settings loaded from environment variables and an optional `.env` file.

Keep secrets out of source control. Copy `.env.example` to `.env` and fill in
API keys before running a live ingest.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration for crawlers, Gemini, pacing, and the demo UI.

    Values can be overridden with environment variables of the same name,
    e.g. `GEMINI_API_KEY=...`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- API keys (optional until a live ingest needs them) ---
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    firecrawl_api_key: str = Field(default="", description="Firecrawl API key")

    # --- Models / fetchers ---
    gemini_model: str = Field(
        default="gemini-3.6-flash",
        description="Gemini model used for unstructured-to-schema extraction",
    )
    default_source_url: str = Field(
        default="https://remoteok.com/api",
        description="Low-risk public job source used by the demo",
    )
    default_source_name: str = Field(default="remoteok")

    # --- Pacing and resilience (never escalate after 429) ---
    request_timeout_seconds: float = 30.0
    max_retries: int = 3
    backoff_base_seconds: float = 1.0
    min_request_interval_seconds: float = 1.5
    circuit_failure_threshold: int = 3
    circuit_cooldown_seconds: float = 60.0
    max_jobs_per_ingest: int = 25

    # --- Selenium ---
    selenium_headless: bool = True
    selenium_page_load_timeout: float = 25.0

    # --- Flask ---
    flask_host: str = "127.0.0.1"
    flask_port: int = 8000
    flask_debug: bool = False

    @property
    def gemini_configured(self) -> bool:
        """True when a Gemini key is present so extraction can run."""
        return bool(self.gemini_api_key.strip())

    @property
    def firecrawl_configured(self) -> bool:
        """True when Firecrawl can be used as the primary fetcher."""
        return bool(self.firecrawl_api_key.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a process-wide Settings singleton.

    Cached so every module sees the same values after first load.
    """
    return Settings()
