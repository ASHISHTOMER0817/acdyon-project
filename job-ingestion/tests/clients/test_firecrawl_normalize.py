"""Firecrawl SDK response normalisation tests."""

from app.clients.firecrawl import _normalize_scrape_payload


class _DocumentMetadata:
    statusCode = 200


class _Document:
    markdown = "# Jobs"
    html = "<h1>Jobs</h1>"
    metadata = _DocumentMetadata()


class _ScrapeResponse:
    data = _Document()


def test_normalize_typed_sdk_objects():
    parsed = _normalize_scrape_payload(_ScrapeResponse())
    assert parsed["markdown"] == "# Jobs"
    assert parsed["html"] == "<h1>Jobs</h1>"
    assert parsed["status_code"] == 200
