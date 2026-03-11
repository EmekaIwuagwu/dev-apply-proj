"""
detector.py — OpenCV-based visual element detection.

Analyses screenshot numpy arrays to locate:
  - Buttons       (rectangular, aspect > 1.5, button-height)
  - Input fields  (wide thin rectangles with borders)
  - Text blocks   (large content regions for the job description)
  - Horizontal rules / section separators

This runs BEFORE the Gemini AI Eye and provides low-level spatial
context that helps the AI Eye understand where to look.
"""
import logging
from typing import List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_buttons(bgr: np.ndarray) -> List[dict]:
    """
    Return candidate button regions sorted by vertical position.
    Each region: {x, y, w, h, cx, cy, area, aspect, confidence}
    """
    regions = _find_rectangular_regions(bgr)
    buttons = []
    for r in regions:
        # Buttons are wider than tall and a button-ish height
        if 1.5 < r["aspect"] < 14 and 24 < r["h"] < 80 and r["w"] > 60:
            r["label"] = "button?"
            r["confidence"] = _button_confidence(bgr, r)
            buttons.append(r)

    buttons.sort(key=lambda r: r["y"])
    return buttons


def find_input_fields(bgr: np.ndarray) -> List[dict]:
    """
    Return candidate input field regions.
    Input fields are wide thin rectangles.
    """
    regions = _find_rectangular_regions(bgr)
    fields = []
    for r in regions:
        if r["aspect"] > 2.5 and 20 < r["h"] < 55 and r["w"] > 100:
            r["label"] = "input?"
            fields.append(r)

    fields.sort(key=lambda r: r["y"])
    return fields


def find_content_blocks(bgr: np.ndarray) -> List[dict]:
    """
    Find large rectangular content regions (e.g. job description body).
    Useful for deciding where to scroll or take a closer crop.
    """
    regions = _find_rectangular_regions(bgr)
    blocks = [
        r for r in regions
        if r["area"] > bgr.shape[0] * bgr.shape[1] * 0.1
        and r["aspect"] < 5
    ]
    blocks.sort(key=lambda r: r["area"], reverse=True)
    return blocks[:5]


def has_captcha_visual(bgr: np.ndarray) -> bool:
    """
    Lightweight check: look for the distinctive reCAPTCHA / hCaptcha
    checkbox region by colour and shape heuristics.
    (Secondary check — the AI Eye does the authoritative one.)
    """
    # reCAPTCHA checkbox is typically ~300×75 px with a white background
    # and a bordered div — we look for a cluster of thin-lined rectangles
    # in the lower-mid area of the viewport.
    h, w = bgr.shape[:2]
    region = bgr[h // 2 :, :]  # bottom half
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    small_rects = 0
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if 200 < cw < 400 and 40 < ch < 100:
            small_rects += 1
    return small_rects >= 2


def dominant_colours(bgr: np.ndarray, k: int = 5) -> List[tuple]:
    """Return k dominant BGR colours via k-means (for button colour matching)."""
    data = bgr.reshape((-1, 3)).astype(np.float32)
    _, labels, centres = cv2.kmeans(
        data, k,
        None,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0),
        5,
        cv2.KMEANS_PP_CENTERS,
    )
    counts = np.bincount(labels.flatten())
    order = np.argsort(counts)[::-1]
    return [tuple(map(int, centres[i])) for i in order]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_rectangular_regions(bgr: np.ndarray) -> List[dict]:
    """
    Core contour pipeline:
      grayscale → Gaussian blur → Canny edges → dilate → find contours
      → filter by size → return bounding-box dicts.
    """
    h_img, w_img = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 30, 120)

    # Dilate so nearby edge segments merge into closed rectangles
    kernel = np.ones((2, 2), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=2)

    contours, _ = cv2.findContours(
        dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    regions = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        aspect = w / h if h > 0 else 0

        # Skip: too small, full-page wide (nav), or tiny noise
        if area < 300:
            continue
        if w > w_img * 0.95 or h > h_img * 0.95:
            continue
        if w < 15 or h < 10:
            continue

        regions.append({
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "cx": x + w // 2,
            "cy": y + h // 2,
            "area": area,
            "aspect": round(aspect, 2),
        })

    return regions


def _button_confidence(bgr: np.ndarray, r: dict) -> str:
    """
    Heuristic confidence for whether a region is a real button.
    Checks interior colour contrast and border presence.
    """
    x, y, w, h = r["x"], r["y"], r["w"], r["h"]
    roi = bgr[y : y + h, x : x + w]
    if roi.size == 0:
        return "low"

    # Buttons usually have a uniform interior with a border
    std = np.std(roi)
    if std < 20:
        return "high"   # very uniform interior = likely a flat button
    if std < 50:
        return "medium"
    return "low"
