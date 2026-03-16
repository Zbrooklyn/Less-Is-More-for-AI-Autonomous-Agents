"""Mouse and keyboard control — thin wrapper around pyautogui with safety guards."""

import time
from typing import Optional, Tuple

import pyautogui

# Keep pyautogui's FAILSAFE enabled (move mouse to upper-left corner to abort)
pyautogui.FAILSAFE = True

# Default pause between pyautogui actions (seconds)
pyautogui.PAUSE = 0.05


def _validate_coords(x: int, y: int, safe: bool) -> None:
    """Raise ValueError if (x, y) is outside the screen when safe=True."""
    if not safe:
        return
    size = pyautogui.size()
    sw, sh = size.width, size.height
    if x < 0 or y < 0 or x >= sw or y >= sh:
        raise ValueError(
            f"Coordinates ({x}, {y}) are outside screen bounds ({sw}x{sh})"
        )


def _safe_delay(safe: bool) -> None:
    """Add a tiny delay when safe mode is enabled for human-visible pacing."""
    if safe:
        time.sleep(0.05)


# ---------------------------------------------------------------------------
# Mouse
# ---------------------------------------------------------------------------

def click(x: int, y: int, safe: bool = True) -> None:
    """Left-click at the given screen coordinates."""
    _validate_coords(x, y, safe)
    _safe_delay(safe)
    pyautogui.click(x, y)


def double_click(x: int, y: int, safe: bool = True) -> None:
    """Double left-click at the given screen coordinates."""
    _validate_coords(x, y, safe)
    _safe_delay(safe)
    pyautogui.doubleClick(x, y)


def right_click(x: int, y: int, safe: bool = True) -> None:
    """Right-click at the given screen coordinates."""
    _validate_coords(x, y, safe)
    _safe_delay(safe)
    pyautogui.rightClick(x, y)


def move_to(x: int, y: int, safe: bool = True) -> None:
    """Move the mouse cursor to the given screen coordinates."""
    _validate_coords(x, y, safe)
    _safe_delay(safe)
    pyautogui.moveTo(x, y)


def scroll(clicks: int, x: Optional[int] = None, y: Optional[int] = None, safe: bool = True) -> None:
    """
    Scroll the mouse wheel.

    Args:
        clicks: Positive = up, negative = down.
        x, y:   Optional position to scroll at. If omitted, scrolls at current position.
        safe:   Validate coordinates if provided.
    """
    if x is not None and y is not None:
        _validate_coords(x, y, safe)
        _safe_delay(safe)
        pyautogui.scroll(clicks, x, y)
    else:
        _safe_delay(safe)
        pyautogui.scroll(clicks)


def get_mouse_position() -> Tuple[int, int]:
    """Return the current (x, y) position of the mouse cursor."""
    pos = pyautogui.position()
    return (pos.x, pos.y)


def get_screen_size() -> Tuple[int, int]:
    """Return the (width, height) of the primary screen in pixels."""
    size = pyautogui.size()
    return (size.width, size.height)


# ---------------------------------------------------------------------------
# Keyboard
# ---------------------------------------------------------------------------

def type_text(text: str, interval: float = 0.05, safe: bool = True) -> None:
    """
    Type a string character by character.

    Args:
        text:     The text to type.
        interval: Seconds between each keystroke.
        safe:     Add a small pre-delay.
    """
    _safe_delay(safe)
    pyautogui.typewrite(text, interval=interval)


def press_key(key: str, safe: bool = True) -> None:
    """
    Press and release a single key (e.g. 'enter', 'tab', 'escape', 'f5').

    See pyautogui.KEYBOARD_KEYS for the full list of accepted key names.
    """
    _safe_delay(safe)
    pyautogui.press(key)


def hotkey(*keys: str, safe: bool = True) -> None:
    """
    Press a key combination (e.g. hotkey('ctrl', 'c')).

    Keys are pressed in order and released in reverse order.
    """
    _safe_delay(safe)
    pyautogui.hotkey(*keys)
