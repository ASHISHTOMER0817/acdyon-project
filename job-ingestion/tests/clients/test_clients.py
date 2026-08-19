"""Client-level tests without hitting vendor APIs."""

from app.clients.gemini import GeminiClient
from app.clients.selenium import SeleniumClient


def test_gemini_json_fence_parse():
    payload = GeminiClient._parse_json('```json\n{"jobs": []}\n```')
    assert payload == {"jobs": []}


def test_challenge_detection():
    html = "<html><body>Verify you are human — recaptcha</body></html>"
    assert SeleniumClient._looks_like_challenge(html, "Just a moment") is True
    assert SeleniumClient._looks_like_challenge("<p>Software Engineer jobs</p>", "Jobs") is False
