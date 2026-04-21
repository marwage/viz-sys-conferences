from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class FetchResult:
    """Result of fetching a URL."""

    html: str
    used_playwright: bool


class HttpClient:
    """HTTP client with a browser-like User-Agent and Playwright fallback on 403."""

    def __init__(self, rate_limit_delay: float = 1.5) -> None:
        self._client = httpx.Client(
            headers={"User-Agent": _BROWSER_UA},
            follow_redirects=True,
            timeout=30.0,
        )
        self._delay = rate_limit_delay

    def fetch(self, url: str) -> FetchResult:
        """Fetch a URL, falling back to Playwright if a 403 is returned.

        Args:
            url: The URL to fetch.

        Returns:
            FetchResult containing the page HTML.
        """
        try:
            result = self._fetch_httpx(url)
            return result
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                return self._fetch_playwright(url)
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
    )
    def _fetch_httpx(self, url: str) -> FetchResult:
        resp = self._client.get(url)
        resp.raise_for_status()
        time.sleep(self._delay)
        return FetchResult(html=resp.text, used_playwright=False)

    def _fetch_playwright(self, url: str) -> FetchResult:
        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=60_000)
                html = page.content()
                browser.close()
        except Exception as exc:
            raise RuntimeError(f"Playwright failed for {url}: {exc}") from exc

        time.sleep(self._delay)
        return FetchResult(html=html, used_playwright=True)

    def close(self) -> None:
        """Close the underlying httpx client."""
        self._client.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
