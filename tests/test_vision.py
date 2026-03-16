"""Tests for the vision module — all screen/input operations are mocked."""

import io
import struct
import types
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytest
from PIL import Image

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _solid_image(color=(128, 64, 32), size=(100, 80)) -> Image.Image:
    """Create a solid-colour RGB image for testing."""
    return Image.new("RGB", size, color)


def _make_mss_grab(image: Image.Image):
    """Build a fake mss grab result that behaves like ScreenShot."""
    arr = np.array(image.convert("RGB"))
    # mss delivers BGRA raw bytes
    h, w = arr.shape[:2]
    bgra = np.zeros((h, w, 4), dtype=np.uint8)
    bgra[:, :, 0] = arr[:, :, 2]  # B
    bgra[:, :, 1] = arr[:, :, 1]  # G
    bgra[:, :, 2] = arr[:, :, 0]  # R
    bgra[:, :, 3] = 255            # A

    grab = MagicMock()
    grab.size = image.size  # (width, height)
    grab.bgra = bgra.tobytes()
    return grab


# ---------------------------------------------------------------------------
# capture.py
# ---------------------------------------------------------------------------

class TestScreenshotToBytes:
    @patch("src.vision.capture.mss.mss")
    def test_returns_png_bytes(self, mock_mss_cls):
        """screenshot_to_bytes should return bytes starting with the PNG header."""
        img = _solid_image()
        mock_sct = MagicMock()
        mock_sct.monitors = [
            {"left": 0, "top": 0, "width": 200, "height": 160},  # all
            {"left": 0, "top": 0, "width": 100, "height": 80},   # primary
        ]
        mock_sct.grab.return_value = _make_mss_grab(img)
        mock_mss_cls.return_value.__enter__ = MagicMock(return_value=mock_sct)
        mock_mss_cls.return_value.__exit__ = MagicMock(return_value=False)

        from src.vision.capture import screenshot_to_bytes
        data = screenshot_to_bytes()

        assert isinstance(data, bytes)
        # PNG magic header: 0x89504E47
        assert data[:4] == b"\x89PNG"


class TestSaveScreenshot:
    @patch("src.vision.capture.mss.mss")
    def test_creates_file(self, mock_mss_cls, tmp_path):
        """save_screenshot should create a file on disk."""
        img = _solid_image()
        mock_sct = MagicMock()
        mock_sct.monitors = [
            {"left": 0, "top": 0, "width": 200, "height": 160},
            {"left": 0, "top": 0, "width": 100, "height": 80},
        ]
        mock_sct.grab.return_value = _make_mss_grab(img)
        mock_mss_cls.return_value.__enter__ = MagicMock(return_value=mock_sct)
        mock_mss_cls.return_value.__exit__ = MagicMock(return_value=False)

        from src.vision.capture import save_screenshot
        dest = tmp_path / "shot.png"
        result = save_screenshot(dest)

        assert result == dest
        assert dest.exists()
        assert dest.stat().st_size > 0


class TestCompareScreenshots:
    def test_identical_images(self):
        """Two identical images should have 100% match."""
        from src.vision.capture import compare_screenshots
        img = _solid_image()
        result = compare_screenshots(img, img.copy())

        assert result["match_percentage"] == 100.0
        assert result["diff_pixels"] == 0
        assert result["diff_regions"] == []

    def test_different_images(self):
        """Two completely different images should have low match percentage."""
        from src.vision.capture import compare_screenshots
        img1 = _solid_image(color=(0, 0, 0))
        img2 = _solid_image(color=(255, 255, 255))
        result = compare_screenshots(img1, img2)

        assert result["match_percentage"] < 10.0
        assert result["diff_pixels"] > 0
        assert isinstance(result["diff_regions"], list)
        assert len(result["diff_regions"]) > 0

    def test_return_structure(self):
        """compare_screenshots should return all expected keys."""
        from src.vision.capture import compare_screenshots
        img = _solid_image()
        result = compare_screenshots(img, img)

        assert "match_percentage" in result
        assert "diff_regions" in result
        assert "total_pixels" in result
        assert "diff_pixels" in result


# ---------------------------------------------------------------------------
# ocr.py
# ---------------------------------------------------------------------------

class TestExtractTextFromImage:
    def test_returns_metadata(self):
        """extract_text_from_image should return image metadata dict."""
        from src.vision.ocr import extract_text_from_image
        img = _solid_image(size=(320, 240))
        result = extract_text_from_image(img)

        assert result["width"] == 320
        assert result["height"] == 240
        assert result["text"] is None
        assert result["ocr_available"] is False
        assert isinstance(result["dominant_colors"], list)
        assert isinstance(result["avg_brightness"], float)


class TestFindTextInImage:
    def test_stub_returns_none(self):
        """find_text_in_image is a stub and should always return None."""
        from src.vision.ocr import find_text_in_image
        img = _solid_image()
        assert find_text_in_image(img, "hello") is None


# ---------------------------------------------------------------------------
# control.py  — mock pyautogui to avoid real mouse/keyboard interaction
# ---------------------------------------------------------------------------

class TestGetScreenSize:
    @patch("src.vision.control.pyautogui")
    def test_returns_positive_dimensions(self, mock_pag):
        mock_pag.size.return_value = types.SimpleNamespace(width=1920, height=1080)
        from src.vision.control import get_screen_size
        w, h = get_screen_size()
        assert w > 0 and h > 0
        assert isinstance(w, int)
        assert isinstance(h, int)


class TestGetMousePosition:
    @patch("src.vision.control.pyautogui")
    def test_returns_int_tuple(self, mock_pag):
        mock_pag.position.return_value = types.SimpleNamespace(x=500, y=300)
        from src.vision.control import get_mouse_position
        pos = get_mouse_position()
        assert isinstance(pos, tuple)
        assert len(pos) == 2
        assert isinstance(pos[0], int) and isinstance(pos[1], int)


class TestClick:
    @patch("src.vision.control.pyautogui")
    def test_click_calls_pyautogui(self, mock_pag):
        mock_pag.size.return_value = types.SimpleNamespace(width=1920, height=1080)
        from src.vision.control import click
        click(100, 200)
        mock_pag.click.assert_called_once_with(100, 200)

    @patch("src.vision.control.pyautogui")
    def test_click_out_of_bounds_raises(self, mock_pag):
        mock_pag.size.return_value = types.SimpleNamespace(width=1920, height=1080)
        from src.vision.control import click
        with pytest.raises(ValueError, match="outside screen bounds"):
            click(5000, 5000)


class TestDoubleClick:
    @patch("src.vision.control.pyautogui")
    def test_double_click_calls_pyautogui(self, mock_pag):
        mock_pag.size.return_value = types.SimpleNamespace(width=1920, height=1080)
        from src.vision.control import double_click
        double_click(100, 200)
        mock_pag.doubleClick.assert_called_once_with(100, 200)


class TestRightClick:
    @patch("src.vision.control.pyautogui")
    def test_right_click_calls_pyautogui(self, mock_pag):
        mock_pag.size.return_value = types.SimpleNamespace(width=1920, height=1080)
        from src.vision.control import right_click
        right_click(100, 200)
        mock_pag.rightClick.assert_called_once_with(100, 200)


class TestTypeText:
    @patch("src.vision.control.pyautogui")
    def test_type_text_no_crash(self, mock_pag):
        from src.vision.control import type_text
        type_text("hello world")
        mock_pag.typewrite.assert_called_once_with("hello world", interval=0.05)


class TestPressKey:
    @patch("src.vision.control.pyautogui")
    def test_press_key_no_crash(self, mock_pag):
        from src.vision.control import press_key
        press_key("enter")
        mock_pag.press.assert_called_once_with("enter")


class TestHotkey:
    @patch("src.vision.control.pyautogui")
    def test_hotkey_no_crash(self, mock_pag):
        from src.vision.control import hotkey
        hotkey("ctrl", "c")
        mock_pag.hotkey.assert_called_once_with("ctrl", "c")


class TestMoveTo:
    @patch("src.vision.control.pyautogui")
    def test_move_to_calls_pyautogui(self, mock_pag):
        mock_pag.size.return_value = types.SimpleNamespace(width=1920, height=1080)
        from src.vision.control import move_to
        move_to(400, 300)
        mock_pag.moveTo.assert_called_once_with(400, 300)


class TestScroll:
    @patch("src.vision.control.pyautogui")
    def test_scroll_at_position(self, mock_pag):
        mock_pag.size.return_value = types.SimpleNamespace(width=1920, height=1080)
        from src.vision.control import scroll
        scroll(-3, x=500, y=500)
        mock_pag.scroll.assert_called_once_with(-3, 500, 500)

    @patch("src.vision.control.pyautogui")
    def test_scroll_no_position(self, mock_pag):
        from src.vision.control import scroll
        scroll(5)
        mock_pag.scroll.assert_called_once_with(5)


# ---------------------------------------------------------------------------
# automation.py — mock ctypes/user32 to avoid real window operations
# ---------------------------------------------------------------------------

class TestListWindows:
    @patch("src.vision.automation._enum_windows")
    def test_returns_list(self, mock_enum):
        mock_enum.return_value = [
            {"hwnd": 12345, "title": "Notepad", "rect": {"left": 0, "top": 0, "width": 800, "height": 600}},
            {"hwnd": 67890, "title": "Calculator", "rect": {"left": 100, "top": 100, "width": 400, "height": 500}},
        ]
        from src.vision.automation import list_windows
        result = list_windows()
        assert isinstance(result, list)
        assert len(result) == 2
        assert all("title" in w and "rect" in w for w in result)


class TestFindWindow:
    @patch("src.vision.automation._enum_windows")
    def test_finds_matching_window(self, mock_enum):
        mock_enum.return_value = [
            {"hwnd": 1, "title": "My Notepad Window", "rect": {"left": 0, "top": 0, "width": 800, "height": 600}},
        ]
        from src.vision.automation import find_window
        result = find_window("notepad")
        assert result is not None
        assert "Notepad" in result["title"]

    @patch("src.vision.automation._enum_windows")
    def test_returns_none_when_not_found(self, mock_enum):
        mock_enum.return_value = [
            {"hwnd": 1, "title": "Calculator", "rect": {"left": 0, "top": 0, "width": 400, "height": 500}},
        ]
        from src.vision.automation import find_window
        result = find_window("notepad")
        assert result is None


class TestGetWindowRect:
    @patch("src.vision.automation._enum_windows")
    def test_returns_rect_dict(self, mock_enum):
        mock_enum.return_value = [
            {"hwnd": 1, "title": "Chrome", "rect": {"left": 10, "top": 20, "width": 1200, "height": 800}},
        ]
        from src.vision.automation import get_window_rect
        rect = get_window_rect("Chrome")
        assert rect is not None
        assert rect["width"] == 1200
        assert rect["height"] == 800

    @patch("src.vision.automation._enum_windows")
    def test_returns_none_when_missing(self, mock_enum):
        mock_enum.return_value = []
        from src.vision.automation import get_window_rect
        assert get_window_rect("NonExistent") is None


class TestFocusWindow:
    @patch("src.vision.automation.user32")
    @patch("src.vision.automation._enum_windows")
    def test_focus_existing_window(self, mock_enum, mock_user32):
        mock_enum.return_value = [
            {"hwnd": 42, "title": "VS Code", "rect": {"left": 0, "top": 0, "width": 1200, "height": 800}},
        ]
        mock_user32.IsIconic.return_value = False
        from src.vision.automation import focus_window
        assert focus_window("VS Code") is True
        mock_user32.SetForegroundWindow.assert_called_once_with(42)

    @patch("src.vision.automation._enum_windows")
    def test_focus_missing_window(self, mock_enum):
        mock_enum.return_value = []
        from src.vision.automation import focus_window
        assert focus_window("NonExistent") is False
