"""Tests for browser module — search, fetch, extract, screenshot, sync wrapper, lifecycle."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.browser.engine import (
    BrowserEngine,
    ExtractResult,
    PageResult,
    SearchResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_DDG_HTML = """
<html><body>
<div class="result">
  <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage1">
    Example Page 1
  </a>
  <a class="result__snippet">This is the first snippet.</a>
</div>
<div class="result">
  <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage2">
    Example Page 2
  </a>
  <a class="result__snippet">This is the second snippet.</a>
</div>
<div class="result">
  <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage3">
    Example Page 3
  </a>
  <a class="result__snippet">Third snippet here.</a>
</div>
</body></html>
"""

SAMPLE_PAGE_HTML = """
<html>
<head><title>Test Page Title</title></head>
<body>
  <h1>Hello World</h1>
  <p>Some paragraph text.</p>
  <a href="https://example.com/link1">Link One</a>
  <a href="https://example.com/link2">Link Two</a>
  <div class="data-item" data-id="1">Item 1</div>
  <div class="data-item" data-id="2">Item 2</div>
  <script>var x = 1;</script>
  <style>.hidden { display: none; }</style>
</body>
</html>
"""


def _make_mock_response(html: str, status_code: int = 200):
    """Create a mock httpx response."""
    resp = MagicMock()
    resp.text = html
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture
def mock_http_client():
    """Patch httpx.AsyncClient to return mock responses."""
    client = AsyncMock()
    client.get = AsyncMock()
    client.aclose = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# Search tests
# ---------------------------------------------------------------------------

class TestSearch:
    """Test search returns structured results."""

    @pytest.mark.asyncio
    async def test_search_returns_structured_results(self, mock_http_client):
        mock_http_client.get.return_value = _make_mock_response(SAMPLE_DDG_HTML)

        engine = BrowserEngine(use_playwright=False)
        engine._http_client = mock_http_client
        engine._open = True

        results = await engine.search("test query", max_results=5)

        assert isinstance(results, list)
        assert len(results) == 3
        for r in results:
            assert isinstance(r, SearchResult)
            assert r.title
            assert r.url.startswith("https://")
            assert isinstance(r.snippet, str)

    @pytest.mark.asyncio
    async def test_search_respects_max_results(self, mock_http_client):
        mock_http_client.get.return_value = _make_mock_response(SAMPLE_DDG_HTML)

        engine = BrowserEngine(use_playwright=False)
        engine._http_client = mock_http_client
        engine._open = True

        results = await engine.search("test", max_results=1)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_extracts_real_urls(self, mock_http_client):
        mock_http_client.get.return_value = _make_mock_response(SAMPLE_DDG_HTML)

        engine = BrowserEngine(use_playwright=False)
        engine._http_client = mock_http_client
        engine._open = True

        results = await engine.search("test")
        assert results[0].url == "https://example.com/page1"
        assert results[1].url == "https://example.com/page2"

    @pytest.mark.asyncio
    async def test_search_empty_results(self, mock_http_client):
        empty_html = "<html><body><p>No results</p></body></html>"
        mock_http_client.get.return_value = _make_mock_response(empty_html)

        engine = BrowserEngine(use_playwright=False)
        engine._http_client = mock_http_client
        engine._open = True

        results = await engine.search("xyznonexistent")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_raises_when_not_open(self):
        engine = BrowserEngine(use_playwright=False)
        with pytest.raises(RuntimeError, match="not open"):
            await engine.search("test")


# ---------------------------------------------------------------------------
# Fetch page tests
# ---------------------------------------------------------------------------

class TestFetchPage:
    """Test fetch_page returns expected fields."""

    @pytest.mark.asyncio
    async def test_fetch_returns_page_result(self, mock_http_client):
        mock_http_client.get.return_value = _make_mock_response(SAMPLE_PAGE_HTML)

        engine = BrowserEngine(use_playwright=False)
        engine._http_client = mock_http_client
        engine._open = True

        result = await engine.fetch_page("https://example.com")

        assert isinstance(result, PageResult)
        assert result.url == "https://example.com"
        assert result.title == "Test Page Title"
        assert "Hello World" in result.text_content
        assert "Some paragraph text" in result.text_content

    @pytest.mark.asyncio
    async def test_fetch_extracts_links(self, mock_http_client):
        mock_http_client.get.return_value = _make_mock_response(SAMPLE_PAGE_HTML)

        engine = BrowserEngine(use_playwright=False)
        engine._http_client = mock_http_client
        engine._open = True

        result = await engine.fetch_page("https://example.com")

        assert isinstance(result.links, list)
        assert len(result.links) == 2
        assert result.links[0]["href"] == "https://example.com/link1"
        assert result.links[0]["text"] == "Link One"

    @pytest.mark.asyncio
    async def test_fetch_strips_scripts_and_styles(self, mock_http_client):
        mock_http_client.get.return_value = _make_mock_response(SAMPLE_PAGE_HTML)

        engine = BrowserEngine(use_playwright=False)
        engine._http_client = mock_http_client
        engine._open = True

        result = await engine.fetch_page("https://example.com")

        assert "var x = 1" not in result.text_content
        assert ".hidden" not in result.text_content

    @pytest.mark.asyncio
    async def test_fetch_handles_missing_title(self, mock_http_client):
        no_title_html = "<html><body><p>No title tag here.</p></body></html>"
        mock_http_client.get.return_value = _make_mock_response(no_title_html)

        engine = BrowserEngine(use_playwright=False)
        engine._http_client = mock_http_client
        engine._open = True

        result = await engine.fetch_page("https://example.com/notitle")
        assert result.title == ""

    @pytest.mark.asyncio
    async def test_fetch_raises_when_not_open(self):
        engine = BrowserEngine(use_playwright=False)
        with pytest.raises(RuntimeError, match="not open"):
            await engine.fetch_page("https://example.com")


# ---------------------------------------------------------------------------
# Extract data tests
# ---------------------------------------------------------------------------

class TestExtractData:
    """Test extract_data with and without CSS selector."""

    @pytest.mark.asyncio
    async def test_extract_with_selector(self, mock_http_client):
        mock_http_client.get.return_value = _make_mock_response(SAMPLE_PAGE_HTML)

        engine = BrowserEngine(use_playwright=False)
        engine._http_client = mock_http_client
        engine._open = True

        result = await engine.extract_data(
            "https://example.com", selector=".data-item"
        )

        assert isinstance(result, ExtractResult)
        assert result.selector == ".data-item"
        assert len(result.elements) == 2
        assert result.elements[0]["tag"] == "div"
        assert result.elements[0]["text"] == "Item 1"
        assert result.elements[0]["attributes"]["data-id"] == "1"

    @pytest.mark.asyncio
    async def test_extract_without_selector(self, mock_http_client):
        mock_http_client.get.return_value = _make_mock_response(SAMPLE_PAGE_HTML)

        engine = BrowserEngine(use_playwright=False)
        engine._http_client = mock_http_client
        engine._open = True

        result = await engine.extract_data("https://example.com")

        assert isinstance(result, ExtractResult)
        assert result.selector is None
        assert len(result.elements) > 0

    @pytest.mark.asyncio
    async def test_extract_no_matches(self, mock_http_client):
        mock_http_client.get.return_value = _make_mock_response(SAMPLE_PAGE_HTML)

        engine = BrowserEngine(use_playwright=False)
        engine._http_client = mock_http_client
        engine._open = True

        result = await engine.extract_data(
            "https://example.com", selector=".nonexistent"
        )
        assert result.elements == []

    @pytest.mark.asyncio
    async def test_extract_class_attributes_flattened(self, mock_http_client):
        html = '<html><body><div class="foo bar">Text</div></body></html>'
        mock_http_client.get.return_value = _make_mock_response(html)

        engine = BrowserEngine(use_playwright=False)
        engine._http_client = mock_http_client
        engine._open = True

        result = await engine.extract_data("https://example.com", selector="div")
        assert result.elements[0]["attributes"]["class"] == "foo bar"

    @pytest.mark.asyncio
    async def test_extract_raises_when_not_open(self):
        engine = BrowserEngine(use_playwright=False)
        with pytest.raises(RuntimeError, match="not open"):
            await engine.extract_data("https://example.com")


# ---------------------------------------------------------------------------
# Screenshot tests
# ---------------------------------------------------------------------------

class TestScreenshot:
    """Test screenshot creates a file."""

    @pytest.mark.asyncio
    async def test_screenshot_creates_file(self, mock_http_client, tmp_path):
        mock_http_client.get.return_value = _make_mock_response(SAMPLE_PAGE_HTML)

        engine = BrowserEngine(use_playwright=False)
        engine._http_client = mock_http_client
        engine._open = True

        out_path = tmp_path / "shot.png"
        result = await engine.screenshot("https://example.com", out_path)

        # httpx fallback saves as .html instead of .png
        assert result.exists()
        assert result.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_screenshot_fallback_saves_html(self, mock_http_client, tmp_path):
        mock_http_client.get.return_value = _make_mock_response(SAMPLE_PAGE_HTML)

        engine = BrowserEngine(use_playwright=False)
        engine._http_client = mock_http_client
        engine._open = True

        out_path = tmp_path / "shot.png"
        result = await engine.screenshot("https://example.com", out_path)

        # Fallback changes extension to .html
        assert result.suffix == ".html"
        content = result.read_text(encoding="utf-8")
        assert "Screenshot fallback" in content
        assert "https://example.com" in content

    @pytest.mark.asyncio
    async def test_screenshot_creates_parent_dirs(self, mock_http_client, tmp_path):
        mock_http_client.get.return_value = _make_mock_response(SAMPLE_PAGE_HTML)

        engine = BrowserEngine(use_playwright=False)
        engine._http_client = mock_http_client
        engine._open = True

        nested_path = tmp_path / "sub" / "dir" / "shot.png"
        result = await engine.screenshot("https://example.com", nested_path)
        assert result.exists()

    @pytest.mark.asyncio
    async def test_screenshot_raises_when_not_open(self, tmp_path):
        engine = BrowserEngine(use_playwright=False)
        with pytest.raises(RuntimeError, match="not open"):
            await engine.screenshot("https://example.com", tmp_path / "shot.png")


# ---------------------------------------------------------------------------
# Sync wrapper tests
# ---------------------------------------------------------------------------

class TestSyncWrapper:
    """Test sync_api functions call through to async engine."""

    @patch("src.browser.sync_api._search_async")
    def test_sync_search(self, mock_async):
        from src.browser.sync_api import search

        expected = [SearchResult(title="Test", url="https://example.com", snippet="snip")]
        mock_async.return_value = expected

        results = search("test query")
        assert results == expected
        mock_async.assert_called_once_with("test query", max_results=5)

    @patch("src.browser.sync_api._fetch_page_async")
    def test_sync_fetch_page(self, mock_async):
        from src.browser.sync_api import fetch_page

        expected = PageResult(url="https://example.com", title="Test", text_content="Hello", links=[])
        mock_async.return_value = expected

        result = fetch_page("https://example.com")
        assert result == expected
        mock_async.assert_called_once_with("https://example.com")

    @patch("src.browser.sync_api._extract_data_async")
    def test_sync_extract_data(self, mock_async):
        from src.browser.sync_api import extract_data

        expected = ExtractResult(url="https://example.com", selector=".item", elements=[])
        mock_async.return_value = expected

        result = extract_data("https://example.com", selector=".item")
        assert result == expected
        mock_async.assert_called_once_with("https://example.com", selector=".item")

    @patch("src.browser.sync_api._screenshot_async")
    def test_sync_screenshot(self, mock_async, tmp_path):
        from src.browser.sync_api import screenshot

        out = tmp_path / "shot.png"
        mock_async.return_value = out

        result = screenshot("https://example.com", str(out))
        assert result == out
        mock_async.assert_called_once_with("https://example.com", str(out))

    @patch("src.browser.sync_api._search_async")
    def test_sync_search_with_max_results(self, mock_async):
        from src.browser.sync_api import search

        mock_async.return_value = []
        search("test", max_results=3)
        mock_async.assert_called_once_with("test", max_results=3)


# ---------------------------------------------------------------------------
# Browser lifecycle tests
# ---------------------------------------------------------------------------

class TestBrowserLifecycle:
    """Test browser open/close lifecycle."""

    @pytest.mark.asyncio
    async def test_context_manager_opens_and_closes(self):
        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value = mock_instance

            async with BrowserEngine(use_playwright=False) as engine:
                assert engine.is_open
                assert engine.backend == "httpx"

            assert not engine.is_open
            mock_instance.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_manual_open_close(self):
        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value = mock_instance

            engine = BrowserEngine(use_playwright=False)
            assert not engine.is_open

            await engine.open()
            assert engine.is_open

            await engine.close()
            assert not engine.is_open
            mock_instance.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_double_open_is_idempotent(self):
        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value = mock_instance

            engine = BrowserEngine(use_playwright=False)
            await engine.open()
            await engine.open()  # Should not error or create second client
            assert engine.is_open
            await engine.close()

    @pytest.mark.asyncio
    async def test_double_close_is_idempotent(self):
        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value = mock_instance

            engine = BrowserEngine(use_playwright=False)
            await engine.open()
            await engine.close()
            await engine.close()  # Should not error
            assert not engine.is_open

    @pytest.mark.asyncio
    async def test_backend_selection_httpx(self):
        engine = BrowserEngine(use_playwright=False)
        assert engine.backend == "httpx"

    @pytest.mark.asyncio
    async def test_backend_selection_playwright(self):
        engine = BrowserEngine(use_playwright=True)
        assert engine.backend == "playwright"

    @pytest.mark.asyncio
    async def test_playwright_fallback_on_launch_failure(self):
        """If Playwright launch fails, engine should fall back to httpx."""
        with patch("src.browser.engine._playwright_available", return_value=True):
            engine = BrowserEngine()
            assert engine._use_playwright  # starts wanting playwright

        # Patch the playwright open to fail
        with patch.object(engine, "_open_playwright", side_effect=Exception("No browser")):
            with patch("httpx.AsyncClient") as MockClient:
                mock_instance = AsyncMock()
                MockClient.return_value = mock_instance

                await engine.open()
                # Should have fallen back to httpx
                assert engine.backend == "httpx"
                assert engine.is_open

                await engine.close()


# ---------------------------------------------------------------------------
# DDG URL extraction
# ---------------------------------------------------------------------------

class TestDDGUrlExtraction:
    """Test the static helper that unwraps DuckDuckGo redirect URLs."""

    def test_extracts_uddg_param(self):
        href = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage&rut=abc"
        result = BrowserEngine._extract_ddg_url(href)
        assert result == "https://example.com/page"

    def test_direct_url(self):
        href = "https://example.com/direct"
        result = BrowserEngine._extract_ddg_url(href)
        assert result == "https://example.com/direct"

    def test_empty_href(self):
        result = BrowserEngine._extract_ddg_url("")
        assert result == ""

    def test_relative_path_returns_empty(self):
        result = BrowserEngine._extract_ddg_url("/relative/path")
        assert result == ""


# ---------------------------------------------------------------------------
# Form filling
# ---------------------------------------------------------------------------

SAMPLE_FORM_HTML = """
<html><body>
<form action="/submit" method="post">
  <input id="email" name="email" type="text">
  <input id="password" name="password" type="password">
  <button type="submit">Login</button>
</form>
</body></html>
"""

SAMPLE_FORM_RESPONSE = """
<html><head><title>Welcome</title></head><body>
<p>Login successful</p>
</body></html>
"""


class TestFillForm:
    """Test form filling functionality."""

    @pytest.mark.asyncio
    async def test_fill_form_httpx_posts_data(self):
        """httpx backend should POST extracted field names."""
        engine = BrowserEngine(use_playwright=False)
        engine._open = True

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_FORM_RESPONSE
        mock_resp.url = "https://example.com/welcome"
        mock_client.post = AsyncMock(return_value=mock_resp)
        engine._http_client = mock_client

        result = await engine.fill_form(
            "https://example.com/login",
            {"#email": "test@test.com", "#password": "secret"},
        )

        assert result.title == "Welcome"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[1]["data"]["email"] == "test@test.com"
        assert call_args[1]["data"]["password"] == "secret"

    @pytest.mark.asyncio
    async def test_fill_form_raises_when_not_open(self):
        engine = BrowserEngine(use_playwright=False)
        with pytest.raises(RuntimeError, match="not open"):
            await engine.fill_form("https://example.com", {"#x": "y"})


class TestClick:
    """Test click functionality."""

    @pytest.mark.asyncio
    async def test_click_httpx_fallback_returns_page(self):
        """httpx backend can't click, so it just fetches the page."""
        engine = BrowserEngine(use_playwright=False)
        engine._open = True

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.text = "<html><head><title>Page</title></head><body>Content</body></html>"
        mock_resp.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        engine._http_client = mock_client

        result = await engine.click("https://example.com", "#button")
        assert result.title == "Page"

    @pytest.mark.asyncio
    async def test_click_raises_when_not_open(self):
        engine = BrowserEngine(use_playwright=False)
        with pytest.raises(RuntimeError, match="not open"):
            await engine.click("https://example.com", "#button")


# ---------------------------------------------------------------------------
# Cookie management
# ---------------------------------------------------------------------------

class TestCookies:
    """Test cookie/session management."""

    @pytest.mark.asyncio
    async def test_get_cookies_httpx(self):
        engine = BrowserEngine(use_playwright=False)
        engine._open = True

        mock_client = AsyncMock()
        mock_cookies = MagicMock()
        mock_cookies.items.return_value = [("session", "abc123"), ("theme", "dark")]
        mock_client.cookies = mock_cookies
        engine._http_client = mock_client

        cookies = engine.get_cookies()
        assert len(cookies) == 2
        assert cookies[0]["name"] == "session"
        assert cookies[0]["value"] == "abc123"

    @pytest.mark.asyncio
    async def test_set_cookies_httpx(self):
        engine = BrowserEngine(use_playwright=False)
        engine._open = True

        mock_client = AsyncMock()
        mock_cookies = MagicMock()
        mock_client.cookies = mock_cookies
        engine._http_client = mock_client

        await engine.set_cookies([
            {"name": "session", "value": "xyz", "domain": "example.com"},
        ])

        mock_cookies.set.assert_called_once_with("session", "xyz", domain="example.com")

    @pytest.mark.asyncio
    async def test_clear_cookies_httpx(self):
        engine = BrowserEngine(use_playwright=False)
        engine._open = True

        mock_client = AsyncMock()
        mock_cookies = MagicMock()
        mock_client.cookies = mock_cookies
        engine._http_client = mock_client

        await engine.clear_cookies()
        mock_cookies.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cookies_when_not_open(self):
        engine = BrowserEngine(use_playwright=False)
        assert engine.get_cookies() == []

    @pytest.mark.asyncio
    async def test_set_cookies_raises_when_not_open(self):
        engine = BrowserEngine(use_playwright=False)
        with pytest.raises(RuntimeError, match="not open"):
            await engine.set_cookies([{"name": "x", "value": "y"}])
