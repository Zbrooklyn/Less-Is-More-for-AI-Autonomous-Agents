"""Synchronous wrapper for the async BrowserEngine.

Provides simple module-level functions for use from non-async code::

    from src.browser.sync_api import search, fetch_page, extract_data, screenshot

    results = search("python tutorials")
    page = fetch_page("https://example.com")
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from src.browser.engine import (
    BrowserEngine,
    ExtractResult,
    PageResult,
    SearchResult,
)


def _run(coro):
    """Run an async coroutine synchronously.

    Handles the case where an event loop is already running (e.g. Jupyter)
    by creating a new loop in a thread.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already inside an event loop — run in a new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


async def _search_async(query: str, *, max_results: int = 5) -> list[SearchResult]:
    async with BrowserEngine() as engine:
        return await engine.search(query, max_results=max_results)


async def _fetch_page_async(url: str) -> PageResult:
    async with BrowserEngine() as engine:
        return await engine.fetch_page(url)


async def _extract_data_async(url: str, *, selector: str | None = None) -> ExtractResult:
    async with BrowserEngine() as engine:
        return await engine.extract_data(url, selector=selector)


async def _screenshot_async(url: str, path: str | Path) -> Path:
    async with BrowserEngine() as engine:
        return await engine.screenshot(url, path)


def search(query: str, *, max_results: int = 5) -> list[SearchResult]:
    """Search the web via DuckDuckGo. Returns list of SearchResult."""
    return _run(_search_async(query, max_results=max_results))


def fetch_page(url: str) -> PageResult:
    """Fetch a page and return its content and links."""
    return _run(_fetch_page_async(url))


def extract_data(url: str, *, selector: str | None = None) -> ExtractResult:
    """Extract structured data from a page, optionally scoped by CSS selector."""
    return _run(_extract_data_async(url, selector=selector))


def screenshot(url: str, path: str | Path) -> Path:
    """Take a screenshot of a page. Returns the output path."""
    return _run(_screenshot_async(url, path))


async def _fill_form_async(url: str, fields: dict[str, str], submit_selector: str | None = None) -> PageResult:
    async with BrowserEngine() as engine:
        return await engine.fill_form(url, fields, submit_selector)


async def _click_async(url: str, selector: str) -> PageResult:
    async with BrowserEngine() as engine:
        return await engine.click(url, selector)


def fill_form(url: str, fields: dict[str, str], submit_selector: str | None = None) -> PageResult:
    """Fill a form on a page and optionally submit it."""
    return _run(_fill_form_async(url, fields, submit_selector))


def click(url: str, selector: str) -> PageResult:
    """Navigate to a URL and click an element."""
    return _run(_click_async(url, selector))
