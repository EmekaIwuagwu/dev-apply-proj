"""
Human-like browser behaviour — mouse curves, typing cadence, delays.
One Brain instance per user, seeded from their ID for consistent personality.
"""
import asyncio
import random


class Brain:
    def __init__(self, seed: str):
        rng = random.Random(seed)
        self._wpm = rng.randint(45, 90)
        self._typo_rate = rng.uniform(0.02, 0.07)
        self._mouse_noise = rng.uniform(0.1, 0.4)
        self._pre_click = (rng.randint(100, 350), rng.randint(500, 1200))
        self._field_pause = (rng.randint(300, 700), rng.randint(1000, 2500))
        self._post_submit = (rng.randint(1500, 2500), rng.randint(3500, 5500))

    # ------------------------------------------------------------------
    # Text typing
    # ------------------------------------------------------------------

    async def type_text(self, page, selector: str, text: str) -> None:
        """Type text into a field character-by-character with human pacing."""
        try:
            await page.click(selector, timeout=5000)
        except Exception:
            return

        chars_per_sec = (self._wpm * 5) / 60
        base_delay = 1.0 / chars_per_sec  # seconds per char

        for char in text:
            # Occasional typo + correction
            if random.random() < self._typo_rate and char.isalpha():
                wrong = random.choice("qwertyuiopasdfghjklzxcvbnm")
                await page.keyboard.type(wrong)
                await asyncio.sleep(random.uniform(0.08, 0.18))
                await page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.05, 0.1))

            await page.keyboard.type(char)
            jitter = random.gauss(0, base_delay * 0.3)
            await asyncio.sleep(max(0.02, base_delay + jitter))

            # Occasional thinking pause at spaces
            if char == " " and random.random() < 0.06:
                await asyncio.sleep(random.uniform(0.25, 0.8))

    # ------------------------------------------------------------------
    # Mouse + click
    # ------------------------------------------------------------------

    async def click(self, page, selector: str) -> None:
        """Move mouse naturally then click. Falls back to direct click."""
        try:
            el = await page.query_selector(selector)
            if not el:
                await page.click(selector, timeout=5000)
                return

            box = await el.bounding_box()
            if not box:
                await page.click(selector, timeout=5000)
                return

            tx = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
            ty = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
            vp = page.viewport_size or {"width": 1920, "height": 1080}
            sx = vp["width"] / 2 + random.uniform(-100, 100)
            sy = vp["height"] / 2 + random.uniform(-100, 100)

            steps = random.randint(15, 30)
            cx = (sx + tx) / 2 + random.uniform(-50, 50) * self._mouse_noise
            cy = (sy + ty) / 2 + random.uniform(-50, 50) * self._mouse_noise

            for i in range(steps + 1):
                t = i / steps
                x = (1 - t) ** 2 * sx + 2 * (1 - t) * t * cx + t ** 2 * tx
                y = (1 - t) ** 2 * sy + 2 * (1 - t) * t * cy + t ** 2 * ty
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.006, 0.018))

            await asyncio.sleep(random.uniform(*self._pre_click) / 1000)
            await page.mouse.click(tx, ty)

        except Exception:
            try:
                await page.click(selector, timeout=5000)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Pauses
    # ------------------------------------------------------------------

    async def between_fields(self) -> None:
        await asyncio.sleep(random.uniform(*self._field_pause) / 1000)

    async def after_submit(self) -> None:
        await asyncio.sleep(random.uniform(*self._post_submit) / 1000)

    async def sleep(self, min_s: float, max_s: float) -> None:
        await asyncio.sleep(random.uniform(min_s, max_s))

    # ------------------------------------------------------------------
    # Page reading (scroll-through simulation)
    # ------------------------------------------------------------------

    async def read_page(self, page) -> None:
        try:
            total = await page.evaluate("document.body.scrollHeight")
            vp_h = (page.viewport_size or {}).get("height", 1080)
            steps = max(2, total // vp_h)
            for i in range(1, steps + 1):
                y = int((i / steps) * total)
                await page.evaluate(f"window.scrollTo({{top:{y},behavior:'smooth'}})")
                await asyncio.sleep(random.uniform(0.6, 1.4))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Interruption handler (cookie banners, modals)
    # ------------------------------------------------------------------

    async def dismiss_interruptions(self, page) -> None:
        for sel in [
            "button:has-text('Accept all')",
            "button:has-text('Accept cookies')",
            "button:has-text('I agree')",
            "button:has-text('Agree')",
            "button:has-text('OK')",
            "[aria-label='Accept all']",
        ]:
            try:
                btn = await page.wait_for_selector(sel, timeout=1200, state="visible")
                if btn:
                    await self.click(page, sel)
                    await asyncio.sleep(1)
                    return
            except Exception:
                pass
