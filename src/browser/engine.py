"""Browser automation engine — async web search, page fetching, and data extraction.

Supports two backends:
- **Playwright** (preferred): full browser automation with JS rendering, screenshots
- **httpx + BeautifulSoup** (fallback): lightweight HTTP + HTML parsing

The backend is selected automatically: Playwright if chromium is available,
otherwise httpx/bs4.
"""

from __future__ import annotations

import asyncio
import logging
import re
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class SearchResult:
    """A single web search result."""
    title: str
    url: str
    snippet: str


@dataclass
class PageResult:
    """Fetched page content."""
    url: str
    title: str
    text_content: str
    links: list[dict[str, str]] = field(default_factory=list)


@dataclass
class ExtractResult:
    """Extracted data from a page."""
    url: str
    selector: str | None
    elements: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

def _playwright_available() -> bool:
    """Check if Playwright + chromium browser are installed."""
    try:
        from playwright.async_api import async_playwright  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# BrowserEngine
# ---------------------------------------------------------------------------

class BrowserEngine:
    """Async browser engine with context-manager lifecycle.

    Usage::

        async with BrowserEngine() as engine:
            results = await engine.search("python async")
            page = await engine.fetch_page("https://example.com")
    """

    def __init__(self, *, headless: bool = True, use_playwright: bool | None = None):
        self._headless = headless
        # Decide backend
        if use_playwright is None:
            self._use_playwright = _playwright_available()
        else:
            self._use_playwright = use_playwright

        # Playwright state
        self._pw = None
        self._pw_browser = None

        # httpx state
        self._http_client = None

        self._open = False

    # -- lifecycle -----------------------------------------------------------

    async def __aenter__(self) -> BrowserEngine:
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def open(self) -> None:
        """Start the browser / HTTP client."""
        if self._open:
            return

        if self._use_playwright:
            try:
                await self._open_playwright()
            except Exception as exc:
                logger.warning("Playwright launch failed (%s), falling back to httpx", exc)
                self._use_playwright = False
                await self._open_httpx()
        else:
            await self._open_httpx()

        self._open = True

    async def _open_playwright(self) -> None:
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        self._pw_browser = await self._pw.chromium.launch(headless=self._headless)

    async def _open_httpx(self) -> None:
        import httpx
        self._http_client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        )

    async def close(self) -> None:
        """Shut down the browser / HTTP client."""
        if not self._open:
            return

        if self._pw_browser:
            await self._pw_browser.close()
            self._pw_browser = None
        if self._pw:
            await self._pw.stop()
            self._pw = None
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        self._open = False

    @property
    def is_open(self) -> bool:
        return self._open

    @property
    def backend(self) -> str:
        """Return which backend is active."""
        if self._use_playwright:
            return "playwright"
        return "httpx"

    # -- search --------------------------------------------------------------

    async def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        """Search the web via DuckDuckGo HTML (no API key needed).

        Returns up to *max_results* ``SearchResult`` objects.
        """
        if not self._open:
            raise RuntimeError("BrowserEngine is not open — use `async with` or call open()")

        if self._use_playwright:
            return await self._search_playwright(query, max_results=max_results)
        return await self._search_httpx(query, max_results=max_results)

    async def _search_playwright(self, query: str, *, max_results: int) -> list[SearchResult]:
        page = await self._pw_browser.new_page()
        try:
            encoded = urllib.parse.quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded}"
            await page.goto(url, wait_until="domcontentloaded")
            return await self._parse_ddg_playwright(page, max_results)
        finally:
            await page.close()

    async def _parse_ddg_playwright(self, page, max_results: int) -> list[SearchResult]:
        results: list[SearchResult] = []
        items = await page.query_selector_all(".result")
        for item in items[:max_results]:
            title_el = await item.query_selector(".result__a")
            snippet_el = await item.query_selector(".result__snippet")
            title = (await title_el.inner_text()).strip() if title_el else ""
            href = (await title_el.get_attribute("href")) if title_el else ""
            snippet = (await snippet_el.inner_text()).strip() if snippet_el else ""
            url = self._extract_ddg_url(href)
            if title and url:
                results.append(SearchResult(title=title, url=url, snippet=snippet))
        return results

    async def _search_httpx(self, query: str, *, max_results: int) -> list[SearchResult]:
        from bs4 import BeautifulSoup
        encoded = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        resp = await self._http_client.get(url)
        resp.raise_for_status()
        return self._parse_ddg_html(resp.text, max_results)

    def _parse_ddg_html(self, html: str, max_results: int) -> list[SearchResult]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        results: list[SearchResult] = []
        for item in soup.select(".result")[:max_results]:
            a_tag = item.select_one(".result__a")
            snippet_tag = item.select_one(".result__snippet")
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            url = self._extract_ddg_url(href)
            if title and url:
                results.append(SearchResult(title=title, url=url, snippet=snippet))
        return results

    @staticmethod
    def _extract_ddg_url(href: str) -> str:
        """Extract the real URL from a DuckDuckGo redirect link."""
        if not href:
            return ""
        # DDG wraps links: //duckduckgo.com/l/?uddg=<encoded_url>&...
        parsed = urllib.parse.urlparse(href)
        qs = urllib.parse.parse_qs(parsed.query)
        if "uddg" in qs:
            return urllib.parse.unquote(qs["uddg"][0])
        # Direct URL
        if href.startswith("http"):
            return href
        return ""

    # -- fetch_page ----------------------------------------------------------

    async def fetch_page(self, url: str) -> PageResult:
        """Fetch a page and return its text content and links."""
        if not self._open:
            raise RuntimeError("BrowserEngine is not open — use `async with` or call open()")

        if self._use_playwright:
            return await self._fetch_playwright(url)
        return await self._fetch_httpx(url)

    async def _fetch_playwright(self, url: str) -> PageResult:
        page = await self._pw_browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded")
            title = await page.title()
            text = await page.inner_text("body")
            links = await self._extract_links_playwright(page)
            return PageResult(url=url, title=title, text_content=text, links=links)
        finally:
            await page.close()

    async def _extract_links_playwright(self, page) -> list[dict[str, str]]:
        links = []
        for a in await page.query_selector_all("a[href]"):
            href = await a.get_attribute("href")
            text = (await a.inner_text()).strip()
            if href:
                links.append({"href": href, "text": text})
        return links

    async def _fetch_httpx(self, url: str) -> PageResult:
        from bs4 import BeautifulSoup
        resp = await self._http_client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        # Remove script/style for cleaner text
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        links = []
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            link_text = a.get_text(strip=True)
            if href:
                links.append({"href": href, "text": link_text})
        return PageResult(url=url, title=title, text_content=text, links=links)

    # -- extract_data --------------------------------------------------------

    async def extract_data(self, url: str, *, selector: str | None = None) -> ExtractResult:
        """Extract structured data from a page, optionally scoped by CSS selector.

        Each matched element is returned as a dict with ``tag``, ``text``,
        and ``attributes`` keys.
        """
        if not self._open:
            raise RuntimeError("BrowserEngine is not open — use `async with` or call open()")

        if self._use_playwright:
            return await self._extract_playwright(url, selector)
        return await self._extract_httpx(url, selector)

    async def _extract_playwright(self, url: str, selector: str | None) -> ExtractResult:
        page = await self._pw_browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded")
            css = selector or "body *"
            elements = []
            for el in await page.query_selector_all(css):
                tag = await el.evaluate("e => e.tagName.toLowerCase()")
                text = (await el.inner_text()).strip()
                attrs = await el.evaluate(
                    "e => Object.fromEntries([...e.attributes].map(a => [a.name, a.value]))"
                )
                elements.append({"tag": tag, "text": text, "attributes": attrs})
            return ExtractResult(url=url, selector=selector, elements=elements)
        finally:
            await page.close()

    async def _extract_httpx(self, url: str, selector: str | None) -> ExtractResult:
        from bs4 import BeautifulSoup
        resp = await self._http_client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        css = selector or "body *"
        elements = []
        for el in soup.select(css):
            tag = el.name
            text = el.get_text(strip=True)
            attrs = dict(el.attrs) if el.attrs else {}
            # Flatten list-valued attrs (e.g. class) to strings
            for k, v in attrs.items():
                if isinstance(v, list):
                    attrs[k] = " ".join(v)
            elements.append({"tag": tag, "text": text, "attributes": attrs})
        return ExtractResult(url=url, selector=selector, elements=elements)

    # -- screenshot ----------------------------------------------------------

    async def screenshot(self, url: str, path: str | Path) -> Path:
        """Take a screenshot of a page. Returns the output path.

        Requires Playwright backend. With httpx fallback, creates a
        placeholder text file noting that screenshots need a real browser.
        """
        if not self._open:
            raise RuntimeError("BrowserEngine is not open — use `async with` or call open()")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if self._use_playwright:
            return await self._screenshot_playwright(url, path)
        return await self._screenshot_httpx(url, path)

    async def _screenshot_playwright(self, url: str, path: Path) -> Path:
        page = await self._pw_browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await page.screenshot(path=str(path), full_page=True)
            return path
        finally:
            await page.close()

    # -- interact (form filling, clicking, navigation) ------------------------

    async def fill_form(self, url: str, fields: dict[str, str], submit_selector: str | None = None) -> PageResult:
        """Navigate to a URL, fill form fields, optionally submit.

        Args:
            url: Page URL containing the form
            fields: Dict of {selector: value} to fill (e.g., {"#email": "test@example.com"})
            submit_selector: CSS selector for submit button (clicked if provided)

        Returns:
            PageResult of the page after filling/submitting.
        """
        if not self._open:
            raise RuntimeError("BrowserEngine is not open")

        if self._use_playwright:
            return await self._fill_form_playwright(url, fields, submit_selector)
        return await self._fill_form_httpx(url, fields)

    async def _fill_form_playwright(self, url: str, fields: dict[str, str], submit_selector: str | None) -> PageResult:
        page = await self._pw_browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded")
            for selector, value in fields.items():
                await page.fill(selector, value)
            if submit_selector:
                await page.click(submit_selector)
                await page.wait_for_load_state("domcontentloaded")
            title = await page.title()
            text = await page.inner_text("body")
            final_url = page.url
            return PageResult(url=final_url, title=title, text_content=text)
        finally:
            await page.close()

    async def _fill_form_httpx(self, url: str, fields: dict[str, str]) -> PageResult:
        """Fallback: POST form data via httpx (no JS, no clicking)."""
        # Extract field names from selectors (best-effort: #id → id, [name=x] → x)
        form_data = {}
        for selector, value in fields.items():
            if selector.startswith("#"):
                form_data[selector[1:]] = value
            elif "name=" in selector:
                import re as _re
                m = _re.search(r'name=["\']?(\w+)', selector)
                if m:
                    form_data[m.group(1)] = value
            else:
                form_data[selector] = value

        resp = await self._http_client.post(url, data=form_data)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return PageResult(url=str(resp.url), title=title, text_content=text)

    async def click(self, url: str, selector: str) -> PageResult:
        """Navigate to a URL and click an element.

        Only works with Playwright backend. Httpx fallback returns the page as-is.
        """
        if not self._open:
            raise RuntimeError("BrowserEngine is not open")

        if self._use_playwright:
            page = await self._pw_browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded")
                await page.click(selector)
                await page.wait_for_load_state("domcontentloaded")
                title = await page.title()
                text = await page.inner_text("body")
                return PageResult(url=page.url, title=title, text_content=text)
            finally:
                await page.close()
        else:
            return await self.fetch_page(url)

    async def navigate(self, url: str, *, wait_for: str = "domcontentloaded") -> PageResult:
        """Navigate to a URL and return the page. Alias for fetch_page with explicit wait."""
        return await self.fetch_page(url)

    # -- cookie/session management -------------------------------------------

    def get_cookies(self) -> list[dict]:
        """Get all cookies from the current session.

        Playwright: returns browser context cookies.
        httpx: returns cookies from the HTTP client jar.
        """
        if not self._open:
            return []

        if self._use_playwright and self._pw_browser:
            # Playwright cookies need an async call, return empty for sync access
            # Use get_cookies_async() for full access
            return []
        elif self._http_client:
            return [
                {"name": name, "value": value, "domain": ""}
                for name, value in self._http_client.cookies.items()
            ]
        return []

    async def get_cookies_async(self) -> list[dict]:
        """Get all cookies (async version for Playwright)."""
        if not self._open:
            return []

        if self._use_playwright and self._pw_browser:
            contexts = self._pw_browser.contexts
            if contexts:
                return await contexts[0].cookies()
            return []
        return self.get_cookies()

    async def set_cookies(self, cookies: list[dict]):
        """Set cookies on the session.

        Args:
            cookies: List of dicts with at minimum {name, value, url or domain}.
        """
        if not self._open:
            raise RuntimeError("BrowserEngine is not open")

        if self._use_playwright and self._pw_browser:
            contexts = self._pw_browser.contexts
            if contexts:
                await contexts[0].add_cookies(cookies)
        elif self._http_client:
            for cookie in cookies:
                self._http_client.cookies.set(
                    cookie["name"], cookie["value"],
                    domain=cookie.get("domain", ""),
                )

    async def clear_cookies(self):
        """Clear all cookies."""
        if not self._open:
            return

        if self._use_playwright and self._pw_browser:
            contexts = self._pw_browser.contexts
            if contexts:
                await contexts[0].clear_cookies()
        elif self._http_client:
            self._http_client.cookies.clear()

    # -- screenshot ----------------------------------------------------------

    async def _screenshot_httpx(self, url: str, path: Path) -> Path:
        """Fallback: fetch page HTML and save a summary text file.

        Real screenshots require a browser engine; this provides a
        best-effort alternative.
        """
        from bs4 import BeautifulSoup
        resp = await self._http_client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else "(no title)"

        # If the path ends in .png/.jpg, swap to .txt since we can't render
        if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            path = path.with_suffix(".html")

        # Save the raw HTML so the caller at least has something
        path.write_text(
            f"<!-- Screenshot fallback (no browser engine) -->\n"
            f"<!-- URL: {url} -->\n"
            f"<!-- Title: {title} -->\n\n"
            f"{resp.text}",
            encoding="utf-8",
        )
        return path
