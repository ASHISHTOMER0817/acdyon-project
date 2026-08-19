"""
Selenium browser client — controlled fallback, not a stealth stack.

Used only when Firecrawl (or plain HTTP) cannot obtain content. If a CAPTCHA
or login wall is detected the client **stops**; it does not try to solve it.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from app.config.logging import get_logger
from app.config.settings import Settings, get_settings

logger = get_logger(__name__)

# Phrases that mean "this page is asking a human to prove they are a human".
_CHALLENGE_MARKERS = (
    "captcha",
    "hcaptcha",
    "recaptcha",
    "cf-challenge",
    "verify you are human",
    "access denied",
    "are you a robot",
)


class SeleniumError(Exception):
    """Raised when the browser fallback cannot retrieve the page."""


class SeleniumClient:
    """
    Headless Chrome via Selenium + webdriver-manager.

    Identity is intentionally boring: a desktop Chrome user-agent and a
    single tab. No fingerprint spoofing, no proxy rotation.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def fetch(self, url: str) -> dict[str, Any]:
        """
        Load `url` in Chrome and return page source.

        Raises SeleniumError on timeout, challenge pages, or driver failures.
        """
        driver = None
        started = time.perf_counter()
        try:
            driver = self._build_driver()
            driver.set_page_load_timeout(self.settings.selenium_page_load_timeout)
            logger.info("Selenium fetching url=%s", url)
            driver.get(url)
            # Brief settle so late-rendered listings can appear. Not a bypass.
            time.sleep(2)
            html = driver.page_source or ""
            title = driver.title or ""
            current = driver.current_url or url
            elapsed_ms = (time.perf_counter() - started) * 1000

            if self._looks_like_challenge(html, title):
                raise SeleniumError(
                    "Page looks like a CAPTCHA or access challenge; stopping as designed"
                )
            if not html.strip() or len(html.strip()) < 50:
                raise SeleniumError("Selenium returned an empty or tiny document")

            return {
                "html": html,
                "markdown": "",
                "status_code": 200,
                "title": title,
                "final_url": current,
                "latency_ms": elapsed_ms,
            }
        except SeleniumError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SeleniumError(str(exc)) from exc
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:  # noqa: BLE001
                    logger.debug("Selenium driver quit failed", exc_info=True)

    def _build_driver(self):
        """Create a Chrome WebDriver, downloading ChromeDriver if needed."""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        if self.settings.selenium_headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1280,720")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    @staticmethod
    def _looks_like_challenge(html: str, title: str) -> bool:
        """Heuristic stop condition — we do not attempt to solve challenges."""
        blob = f"{title}\n{html}".lower()
        return any(marker in blob for marker in _CHALLENGE_MARKERS)
