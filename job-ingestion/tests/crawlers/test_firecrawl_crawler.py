"""Crawler HTTP fallback tests (mocked httpx)."""

from app.crawlers.base import FetchResult
from app.crawlers.firecrawl_crawler import FirecrawlCrawler


class _NoFirecrawl:
    available = False

    def scrape(self, url: str):
        raise AssertionError("should not be called")


def test_http_fallback_json(monkeypatch):
    import httpx

    class _Resp:
        status_code = 200
        text = '{"jobs": [{"title": "Dev"}]}'
        headers = {"content-type": "application/json"}

        def json(self):
            return {"jobs": [{"title": "Dev"}]}

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers=None):
            return _Resp()

    monkeypatch.setattr(httpx, "Client", _Client)
    crawler = FirecrawlCrawler(client=_NoFirecrawl())
    result = crawler.fetch("https://example.com/api")
    assert isinstance(result, FetchResult)
    assert result.ok
    assert result.fetcher == "http"
    assert "Dev" in result.markdown
