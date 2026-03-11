"""
mouse.py — Human-like mouse movement using cubic Bézier curves.

A real human doesn't move a mouse in a straight line.  They follow a
smooth curved path, accelerate at the start, decelerate near the target,
and add tiny micro-jitters throughout.

This module drives Playwright's page.mouse API along Bézier curves so
every movement looks organic.

Usage:
    from agent.browser.mouse import HumanMouse
    mouse = HumanMouse(page, seed="user-uuid")
    await mouse.move_to(x, y)
    await mouse.click(x, y)
    await mouse.hover(x, y)
"""
import asyncio
import logging
import math
import random
from typing import Tuple

from playwright.async_api import Page

logger = logging.getLogger(__name__)


def _cubic_bezier(
    t: float,
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
) -> Tuple[float, float]:
    """Evaluate a cubic Bézier curve at parameter t (0–1)."""
    mt = 1 - t
    x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
    y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
    return x, y


def _ease_in_out(t: float) -> float:
    """Ease-in-out timing function so the mouse accelerates then decelerates."""
    return t * t * (3.0 - 2.0 * t)


class HumanMouse:
    """
    Drives Playwright's mouse along natural Bézier curves.
    Seeded from the user ID so every user has a unique movement personality.
    """

    def __init__(self, page: Page, seed: str = ""):
        self._page = page
        self._rng = random.Random(seed or "default")
        self._cx = 683  # current X (start in viewport centre)
        self._cy = 384  # current Y

        # Per-user personality parameters (seeded, so consistent per user)
        self._speed = self._rng.uniform(0.6, 1.4)   # relative speed (1 = normal)
        self._jitter = self._rng.uniform(0.5, 2.0)  # micro-jitter amplitude (px)
        self._overshoot = self._rng.uniform(0.0, 0.3)  # occasional overshoot

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def move_to(self, x: int, y: int) -> None:
        """Move the mouse from current position to (x, y) along a Bézier curve."""
        # Add small random offset so we never click exactly centre
        tx = x + self._rng.randint(-3, 3)
        ty = y + self._rng.randint(-3, 3)

        await self._bezier_move(self._cx, self._cy, tx, ty)
        self._cx, self._cy = tx, ty

    async def click(self, x: int, y: int, button: str = "left") -> None:
        """Move to (x, y) then click."""
        await self.move_to(x, y)
        # Pre-click pause (human reaction time)
        await asyncio.sleep(self._rng.uniform(0.05, 0.18))
        await self._page.mouse.click(self._cx, self._cy, button=button)
        await asyncio.sleep(self._rng.uniform(0.08, 0.20))

    async def double_click(self, x: int, y: int) -> None:
        """Move to (x, y) then double-click."""
        await self.move_to(x, y)
        await asyncio.sleep(self._rng.uniform(0.05, 0.12))
        await self._page.mouse.dblclick(self._cx, self._cy)
        await asyncio.sleep(self._rng.uniform(0.08, 0.18))

    async def hover(self, x: int, y: int, dwell_s: float = 0.5) -> None:
        """Move to (x, y) and dwell — simulating reading / hover behaviour."""
        await self.move_to(x, y)
        await asyncio.sleep(dwell_s + self._rng.uniform(0, 0.5))

    async def scroll_down(self, amount: int = 300) -> None:
        """Scroll down by `amount` pixels in a human-like chunked way."""
        chunks = self._rng.randint(2, 4)
        per_chunk = amount // chunks
        for _ in range(chunks):
            await self._page.mouse.wheel(0, per_chunk + self._rng.randint(-20, 20))
            await asyncio.sleep(self._rng.uniform(0.3, 0.9))

    async def scroll_to_element(self, x: int, y: int) -> None:
        """Scroll until the element at (x, y) is likely in view, then hover."""
        vp_h = (self._page.viewport_size or {}).get("height", 768)
        if y > vp_h * 0.8:
            scroll_by = int((y - vp_h * 0.5))
            await self.scroll_down(scroll_by)
            await asyncio.sleep(0.5)
        await self.hover(x, y, dwell_s=0.3)

    # ------------------------------------------------------------------
    # Internal: Bézier movement
    # ------------------------------------------------------------------

    async def _bezier_move(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
    ) -> None:
        """
        Move the mouse from (x0, y0) to (x1, y1) along a cubic Bézier curve.

        Control points are randomised so each path is unique.
        Steps and timing are proportional to distance (longer path = slower).
        """
        dist = math.hypot(x1 - x0, y1 - y0)
        if dist < 2:
            # Already there — just update position
            await self._page.mouse.move(x1, y1)
            return

        # Number of steps scales with distance; base speed adjusted by personality
        base_steps = max(10, int(dist / 8))
        steps = self._rng.randint(int(base_steps * 0.8), int(base_steps * 1.3))

        # Two control points displaced perpendicular to the straight path
        mid_x = (x0 + x1) / 2
        mid_y = (y0 + y1) / 2
        perp_x = -(y1 - y0) / dist
        perp_y = (x1 - x0) / dist
        bulge = dist * self._rng.uniform(0.1, 0.4) * self._rng.choice([-1, 1])

        cp1 = (
            x0 + (x1 - x0) * self._rng.uniform(0.2, 0.4) + perp_x * bulge * 0.5,
            y0 + (y1 - y0) * self._rng.uniform(0.2, 0.4) + perp_y * bulge * 0.5,
        )
        cp2 = (
            mid_x + perp_x * bulge,
            mid_y + perp_y * bulge,
        )

        # Timing: total movement time in seconds
        total_time = (dist / 800) / self._speed  # ~800 px/s at speed=1
        total_time = max(0.05, min(total_time, 1.5))

        prev_x, prev_y = x0, y0

        for i in range(1, steps + 1):
            t_raw = i / steps
            t = _ease_in_out(t_raw)  # ease-in-out

            bx, by = _cubic_bezier(t, (x0, y0), cp1, cp2, (x1, y1))

            # Add micro-jitter
            jx = bx + self._rng.gauss(0, self._jitter)
            jy = by + self._rng.gauss(0, self._jitter)

            await self._page.mouse.move(jx, jy)

            # Step duration — slightly variable to look natural
            step_time = (total_time / steps) * self._rng.uniform(0.7, 1.3)
            await asyncio.sleep(step_time)

        # Final precise move to exact target
        await self._page.mouse.move(x1, y1)
