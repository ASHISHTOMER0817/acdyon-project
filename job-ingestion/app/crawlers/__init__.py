"""Crawler adapters: Firecrawl primary, Selenium fallback."""

from app.crawlers.base import BaseCrawler, FetchResult
from app.crawlers.firecrawl_crawler import FirecrawlCrawler
from app.crawlers.selenium_crawler import SeleniumCrawler

__all__ = ["BaseCrawler", "FetchResult", "FirecrawlCrawler", "SeleniumCrawler"]
