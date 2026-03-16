"""Browser module — web search, page fetching, and data extraction."""

from src.browser.engine import BrowserEngine
from src.browser.sync_api import search, fetch_page, extract_data, screenshot

__all__ = [
    "BrowserEngine",
    "search",
    "fetch_page",
    "extract_data",
    "screenshot",
]
