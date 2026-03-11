"""
screen.py — Screenshot capture and image conversion utilities.

Takes Playwright page screenshots and converts them into:
  - raw PNG bytes  → sent to Gemini Vision API
  - numpy BGR array → processed by OpenCV
  - PIL Image       → sent to Gemini Vision API

All vision operations start here.
"""
import io
import logging
from typing import Tuple

import cv2
import numpy as np
from PIL import Image
from playwright.async_api import Page

logger = logging.getLogger(__name__)

# Agent browses at a consistent viewport so coordinate math is stable.
VIEWPORT_W = 1366
VIEWPORT_H = 768
VIEWPORT = {"width": VIEWPORT_W, "height": VIEWPORT_H}


async def capture(page: Page) -> Tuple[bytes, np.ndarray, Image.Image]:
    """
    Capture the current visible viewport (not full-page).

    Returns:
        raw_bytes  — PNG bytes, ready to send to Gemini Vision
        bgr_array  — OpenCV-compatible numpy array (H×W×3, BGR)
        pil_image  — PIL Image (RGB), also accepted by Gemini Vision
    """
    raw = await page.screenshot(type="png", full_page=False)
    pil = Image.open(io.BytesIO(raw)).convert("RGB")
    bgr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    return raw, bgr, pil


async def capture_region(
    page: Page,
    x: int,
    y: int,
    w: int,
    h: int,
) -> Tuple[bytes, np.ndarray]:
    """
    Capture and crop to a specific rectangle on the page.
    Useful for zooming into a form section before analysis.
    """
    raw, bgr, _ = await capture(page)
    cropped_bgr = bgr[y : y + h, x : x + w]
    # Re-encode crop as PNG bytes for Gemini
    _, buf = cv2.imencode(".png", cropped_bgr)
    return bytes(buf), cropped_bgr


def pct_to_px(x_pct: float, y_pct: float) -> Tuple[int, int]:
    """Convert 0–1 percentage coordinates → pixel coordinates."""
    return int(x_pct * VIEWPORT_W), int(y_pct * VIEWPORT_H)


def px_to_pct(x: int, y: int) -> Tuple[float, float]:
    """Convert pixel coordinates → 0–1 percentage coordinates."""
    return x / VIEWPORT_W, y / VIEWPORT_H


def draw_debug_boxes(bgr: np.ndarray, regions: list, color=(0, 255, 0)) -> np.ndarray:
    """Draw bounding boxes on a copy of the frame — for debugging."""
    frame = bgr.copy()
    for r in regions:
        x, y, w, h = r["x"], r["y"], r["w"], r["h"]
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        if label := r.get("label"):
            cv2.putText(
                frame, label, (x, max(y - 5, 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1,
            )
    return frame
