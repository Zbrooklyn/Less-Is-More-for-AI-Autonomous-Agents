"""OCR stubs — text extraction from screenshots.

Full OCR (e.g. Tesseract, Windows.Media.Ocr) is a future enhancement.
For now this module provides pragmatic metadata extraction and stub interfaces
so the rest of the agent can program against a stable API.
"""

from typing import Optional, Tuple

import numpy as np
from PIL import Image


def extract_text_from_image(image: Image.Image) -> dict:
    """
    Extract textual information from a screenshot.

    Currently returns image metadata (size, dominant colours, brightness).
    A future version will integrate Windows.Media.Ocr or Tesseract for
    actual character recognition.

    Args:
        image: PIL Image to analyse.

    Returns:
        {
            "text": str | None  — extracted text (None until OCR is wired up),
            "width": int,
            "height": int,
            "dominant_colors": list of (R, G, B) tuples,
            "avg_brightness": float (0–255),
            "ocr_available": bool,
        }
    """
    image = image.convert("RGB")
    arr = np.array(image)

    # Average brightness (simple mean of all channels)
    avg_brightness = float(arr.mean())

    # Dominant colours via simple quantisation
    dominant = _dominant_colors(arr, n=5)

    return {
        "text": None,
        "width": image.width,
        "height": image.height,
        "dominant_colors": dominant,
        "avg_brightness": round(avg_brightness, 2),
        "ocr_available": False,
    }


def find_text_in_image(
    image: Image.Image,
    text: str,
) -> Optional[Tuple[int, int, int, int]]:
    """
    Search for *text* in the image and return its bounding box.

    Returns:
        (x, y, width, height) if found, else None.

    Note:
        This is a stub — always returns None until a real OCR backend is
        integrated.  The interface is intentionally stable so callers can
        rely on it today and gain functionality without code changes later.
    """
    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _dominant_colors(arr: np.ndarray, n: int = 5) -> list:
    """Return the *n* most-common colours by simple 4-bit quantisation."""
    # Quantise to 16 levels per channel → 4096 possible colours
    quantised = (arr // 16) * 16 + 8  # centre of each bucket
    # Flatten to list of (R, G, B)
    pixels = quantised.reshape(-1, 3)
    # Pack into single int for fast counting
    packed = pixels[:, 0].astype(np.int32) * 65536 + pixels[:, 1].astype(np.int32) * 256 + pixels[:, 2].astype(np.int32)
    unique, counts = np.unique(packed, return_counts=True)
    top_idx = counts.argsort()[::-1][:n]
    result = []
    for idx in top_idx:
        val = int(unique[idx])
        r = (val >> 16) & 0xFF
        g = (val >> 8) & 0xFF
        b = val & 0xFF
        result.append((r, g, b))
    return result
