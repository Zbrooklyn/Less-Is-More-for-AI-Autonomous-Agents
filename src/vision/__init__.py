"""Vision module — screenshot capture, OCR stubs, mouse/keyboard control, and Windows UI automation."""

from src.vision.capture import screenshot, screenshot_to_bytes, save_screenshot, compare_screenshots
from src.vision.ocr import extract_text_from_image, find_text_in_image
from src.vision.control import (
    click, double_click, right_click,
    type_text, press_key, hotkey,
    move_to, scroll,
    get_mouse_position, get_screen_size,
)
from src.vision.automation import find_window, get_window_rect, focus_window, list_windows

__all__ = [
    # capture
    "screenshot", "screenshot_to_bytes", "save_screenshot", "compare_screenshots",
    # ocr
    "extract_text_from_image", "find_text_in_image",
    # control
    "click", "double_click", "right_click",
    "type_text", "press_key", "hotkey",
    "move_to", "scroll",
    "get_mouse_position", "get_screen_size",
    # automation
    "find_window", "get_window_rect", "focus_window", "list_windows",
]
