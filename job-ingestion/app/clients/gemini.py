"""
Gemini client — unstructured-to-structured extraction only.

Gemini is **not** the final validator. Callers must run JobValidator on
every object before it is stored.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.config.logging import get_logger
from app.config.settings import Settings, get_settings
from app.utils.debug_dump import dump_gemini

logger = get_logger(__name__)

# Instruct the model to return only this envelope so parsing stays deterministic.
_EXTRACTION_PROMPT = """You extract job listings from crawled page content.

Return ONLY valid JSON matching this schema (no markdown fences):
{{
  "jobs": [
    {{
      "title": "string (required)",
      "company": "string (required)",
      "source_url": "string (required, absolute URL of the listing if known, else the page URL)",
      "location": "string or null",
      "salary": {{"min": number or null, "max": number or null, "currency": "string or null"}} or null,
      "posted_at": "string or null",
      "description": "string or null",
      "source": "string or null"
    }}
  ],
  "notes": "string or null"
}}

Rules:
- Skip ads, navigation, and unrelated page chrome.
- Do not invent companies, salaries, or URLs. Use null when unknown.
- Prefer fewer accurate listings over many guessed ones.
- Cap output at {max_jobs} jobs.
- Page URL: {page_url}
- Source name: {source_name}

Content:
{content}
"""


class GeminiError(Exception):
    """Raised when Gemini cannot produce parseable structured output."""


class GeminiClient:
    """
    Calls the Gemini API and parses a JSON envelope of job objects.

    Uses `response_mime_type=application/json` when the SDK supports it so
    the model is biased toward valid JSON.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        # "new" = google.genai Client; "old" = google.generativeai GenerativeModel.
        self._sdk: Optional[str] = None
        self._client = None
        self._model = None
        if self.settings.gemini_configured:
            self._init_sdk()

    def _init_sdk(self) -> None:
        """Prefer the current `google.genai` package; fall back to the old SDK."""
        try:
            from google import genai

            self._client = genai.Client(api_key=self.settings.gemini_api_key)
            self._sdk = "new"
            return
        except Exception as exc:  # noqa: BLE001
            logger.info("google.genai unavailable (%s); trying google.generativeai", exc)

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.settings.gemini_api_key)
            self._model = genai.GenerativeModel(self.settings.gemini_model)
            self._sdk = "old"
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gemini SDK unavailable: %s", exc)

    @property
    def available(self) -> bool:
        """True when an API key was accepted by the SDK."""
        return self._sdk is not None

    def extract_jobs(
        self,
        content: str,
        page_url: str,
        source_name: str,
        max_jobs: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Send crawled text to Gemini and return a list of raw job dicts.

        Each dict is the object *as returned by Gemini* (plus light JSON
        parsing). Persistence and Streamlit display happen after this.
        """
        if not self.available:
            raise GeminiError("Gemini is not configured (missing GEMINI_API_KEY)")

        limit = max_jobs or self.settings.max_jobs_per_ingest
        # Bound prompt size so we do not blow the context window on huge HTML.
        clipped = content[:80_000]
        prompt = _EXTRACTION_PROMPT.format(
            max_jobs=limit,
            page_url=page_url,
            source_name=source_name,
            content=clipped,
        )

        logger.info("Calling Gemini model=%s url=%s", self.settings.gemini_model, page_url)
        try:
            response = self._generate(prompt)
        except Exception as exc:  # noqa: BLE001
            raise GeminiError(f"Gemini request failed: {exc}") from exc

        text = self._response_text(response)
        # Dump Gemini prompt + raw response to temp/ for inspection.
        try:
            dump_path = dump_gemini(page_url, prompt, text)
            logger.debug("Gemini exchange saved to %s", dump_path)
        except Exception:  # noqa: BLE001
            pass
        envelope = self._parse_json(text)
        jobs = envelope.get("jobs")
        if not isinstance(jobs, list):
            raise GeminiError("Gemini JSON did not contain a jobs array")

        logger.info("Gemini returned %s job object(s)", len(jobs))
        return [job for job in jobs if isinstance(job, dict)]

    def _generate(self, prompt: str):
        """Prefer JSON mime type; fall back to a plain generate_content call."""
        if self._sdk == "new":
            from google.genai import types

            assert self._client is not None
            config = types.GenerateContentConfig(response_mime_type="application/json")
            try:
                chat = self._client.chats.create(
                    model=self.settings.gemini_model,
                    config=config,
                )
                return chat.send_message(prompt)
            except Exception:  # noqa: BLE001
                # Fallback: plain generate_content without mime type.
                return self._client.models.generate_content(
                    model=self.settings.gemini_model,
                    contents=prompt,
                )

        assert self._model is not None
        try:
            return self._model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"},
            )
        except Exception:  # noqa: BLE001 — older SDK / model may reject mime type
            return self._model.generate_content(prompt)

    @staticmethod
    def _response_text(response: Any) -> str:
        """Pull the text payload out of a GenerativeModel response."""
        text = getattr(response, "text", None)
        if text:
            return text
        # Fallback: concatenate parts if `.text` is empty.
        candidates = getattr(response, "candidates", None) or []
        chunks: list[str] = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                part_text = getattr(part, "text", None)
                if part_text:
                    chunks.append(part_text)
        if not chunks:
            raise GeminiError("Gemini returned no text")
        return "\n".join(chunks)

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        """Parse model output, stripping optional markdown fences."""
        stripped = text.strip()
        fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
        if fenced:
            stripped = fenced.group(1)
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise GeminiError(f"Gemini output was not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise GeminiError("Gemini JSON root was not an object")
        return data
