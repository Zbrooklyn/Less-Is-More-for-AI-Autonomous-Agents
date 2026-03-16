"""Windows UI Automation — window enumeration, focus, and geometry via ctypes."""

import ctypes
import ctypes.wintypes
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Win32 type aliases
# ---------------------------------------------------------------------------
user32 = ctypes.windll.user32  # type: ignore[attr-defined]

EnumWindowsProc = ctypes.WINFUNCTYPE(
    ctypes.wintypes.BOOL,
    ctypes.wintypes.HWND,
    ctypes.wintypes.LPARAM,
)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _get_window_text(hwnd: int) -> str:
    """Return the title bar text for *hwnd*."""
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def _is_window_visible(hwnd: int) -> bool:
    return bool(user32.IsWindowVisible(hwnd))


def _get_rect(hwnd: int) -> Tuple[int, int, int, int]:
    """Return (left, top, width, height) for *hwnd*."""
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)


def _enum_windows() -> List[dict]:
    """Enumerate all visible, titled windows."""
    results: List[dict] = []

    @EnumWindowsProc
    def callback(hwnd, _lparam):
        if _is_window_visible(hwnd):
            title = _get_window_text(hwnd)
            if title:
                left, top, w, h = _get_rect(hwnd)
                results.append({
                    "hwnd": hwnd,
                    "title": title,
                    "rect": {"left": left, "top": top, "width": w, "height": h},
                })
        return True  # continue enumeration

    user32.EnumWindows(callback, 0)
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_windows() -> List[dict]:
    """
    List all visible windows with a non-empty title.

    Returns:
        List of {"hwnd": int, "title": str, "rect": {"left", "top", "width", "height"}}.
    """
    return _enum_windows()


def find_window(title: str) -> Optional[dict]:
    """
    Find the first visible window whose title contains *title* (case-insensitive).

    Returns:
        Window dict or None.
    """
    needle = title.lower()
    for win in _enum_windows():
        if needle in win["title"].lower():
            return win
    return None


def get_window_rect(title: str) -> Optional[dict]:
    """
    Get the position and size of the first window matching *title*.

    Returns:
        {"left": int, "top": int, "width": int, "height": int} or None.
    """
    win = find_window(title)
    return win["rect"] if win else None


def focus_window(title: str) -> bool:
    """
    Bring the first window matching *title* to the foreground.

    Returns:
        True if the window was found and focus was requested, False otherwise.

    Note:
        Windows may block SetForegroundWindow if the calling process is not the
        foreground app. This function uses AllowSetForegroundWindow as a
        best-effort workaround.
    """
    win = find_window(title)
    if win is None:
        return False

    hwnd = win["hwnd"]

    # Best-effort: allow our process to steal focus
    try:
        user32.AllowSetForegroundWindow(ctypes.wintypes.DWORD(-1))  # ASFW_ANY
    except Exception:
        pass

    # If minimised, restore first
    SW_RESTORE = 9
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)

    user32.SetForegroundWindow(hwnd)
    return True
