"""Screenshot capture — fast multi-monitor screenshots via mss, with comparison."""

import io
from pathlib import Path
from typing import Optional, Tuple, Union

import mss
import numpy as np
from PIL import Image


def screenshot(region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
    """
    Capture a screenshot and return a PIL Image.

    Args:
        region: Optional (left, top, width, height) to capture a sub-region.
                If None, captures the full primary monitor.

    Returns:
        PIL Image in RGB mode.
    """
    with mss.mss() as sct:
        if region:
            left, top, width, height = region
            monitor = {"left": left, "top": top, "width": width, "height": height}
        else:
            # Primary monitor (index 1); index 0 is "all monitors combined"
            monitor = sct.monitors[1]

        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    return img


def screenshot_to_bytes(region: Optional[Tuple[int, int, int, int]] = None) -> bytes:
    """
    Capture a screenshot and return PNG bytes.

    Args:
        region: Optional (left, top, width, height).

    Returns:
        PNG-encoded bytes.
    """
    img = screenshot(region)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def save_screenshot(
    path: Union[str, Path],
    region: Optional[Tuple[int, int, int, int]] = None,
) -> Path:
    """
    Capture a screenshot and save to a file.

    Args:
        path: Destination file path (parent directory must exist).
        region: Optional (left, top, width, height).

    Returns:
        Path to the saved file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img = screenshot(region)
    img.save(str(path))
    return path


def compare_screenshots(img1: Image.Image, img2: Image.Image) -> dict:
    """
    Pixel-level comparison of two images.

    Both images are resized to the smaller common dimensions before comparison.

    Args:
        img1: First PIL Image.
        img2: Second PIL Image.

    Returns:
        {
            "match_percentage": float (0.0 – 100.0),
            "diff_regions": list of (x, y, w, h) bounding boxes where differences cluster,
            "total_pixels": int,
            "diff_pixels": int,
        }
    """
    # Normalise to RGB
    img1 = img1.convert("RGB")
    img2 = img2.convert("RGB")

    # Use the smaller dimensions
    w = min(img1.width, img2.width)
    h = min(img1.height, img2.height)
    img1 = img1.resize((w, h))
    img2 = img2.resize((w, h))

    arr1 = np.array(img1, dtype=np.int16)
    arr2 = np.array(img2, dtype=np.int16)

    # Per-pixel difference (absolute, summed across channels)
    diff = np.abs(arr1 - arr2).sum(axis=2)  # shape (h, w)

    # A pixel counts as "different" if the channel-sum difference exceeds a threshold
    threshold = 30  # generous tolerance for anti-aliasing, compression artefacts
    diff_mask = diff > threshold

    total_pixels = w * h
    diff_pixels = int(diff_mask.sum())
    match_pct = 100.0 * (1 - diff_pixels / total_pixels) if total_pixels else 100.0

    # Find bounding boxes of contiguous diff regions (simple row-scan approach)
    diff_regions = _find_diff_regions(diff_mask)

    return {
        "match_percentage": round(match_pct, 2),
        "diff_regions": diff_regions,
        "total_pixels": total_pixels,
        "diff_pixels": diff_pixels,
    }


def _find_diff_regions(mask: np.ndarray, block: int = 32) -> list:
    """
    Divide the diff mask into blocks and return bounding boxes for blocks that
    contain differences.  This avoids expensive connected-component analysis.
    """
    h, w = mask.shape
    regions = []
    for y0 in range(0, h, block):
        for x0 in range(0, w, block):
            y1 = min(y0 + block, h)
            x1 = min(x0 + block, w)
            if mask[y0:y1, x0:x1].any():
                regions.append((x0, y0, x1 - x0, y1 - y0))
    return regions
