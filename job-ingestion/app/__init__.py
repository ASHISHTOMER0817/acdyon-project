"""
Job listing ingestion package.

Fetch (Firecrawl → Selenium fallback) → preserve raw crawl → preprocess →
Gemini structured extraction → validate → store in process memory → expose
via Streamlit and an optional Flask API.
"""

__version__ = "0.1.0"
