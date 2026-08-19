"""
Tests for the Gemini extractor using a fake client.

No network, no API key — we only check that objects pass through.
"""

from __future__ import annotations

from app.extractors.gemini_extractor import GeminiExtractor


class _FakeGeminiClient:
    available = True

    def extract_jobs(self, content, page_url, source_name, max_jobs=None):
        return [
            {
                "title": "Engineer",
                "company": "Acme",
                "source_url": page_url,
                "location": "Remote",
                "source": source_name,
            }
        ]


def test_extractor_returns_gemini_objects():
    extractor = GeminiExtractor(client=_FakeGeminiClient())
    jobs = extractor.extract("Software Engineer at Acme", "https://example.com", "example")
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Engineer"


def test_extractor_skips_empty_content():
    extractor = GeminiExtractor(client=_FakeGeminiClient())
    assert extractor.extract("   ", "https://example.com", "example") == []
