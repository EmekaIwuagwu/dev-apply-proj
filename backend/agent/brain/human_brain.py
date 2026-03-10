import random
import asyncio
import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class BehaviourProfile:
    """
    Per-user personality that stays consistent across runs.
    Seeded from user UUID so behaviour is reproducible per user.
    """
    typing_wpm: int              # Words per minute: 40–95
    typo_rate: float             # Probability of a typo: 0.02–0.08
    read_speed_ms_per_word: int  # Time to 'read' a page: 180–320ms per word
    scroll_pause_variance: float # How much scroll pause varies: 0.2–0.6
    mouse_curve_noise: float     # How curved mouse paths are: 0.1–0.4
    pre_click_hesitation: tuple  # (min_ms, max_ms) before clicking a button: (200, 1200)
    between_field_pause: tuple   # (min_ms, max_ms) between form fields: (400, 2200)
    post_submit_wait: tuple      # (min_ms, max_ms) after clicking submit: (1500, 4000)


class HumanBrain:
    def __init__(self, personality_seed: str):
        rng = random.Random(personality_seed)
        self.profile = BehaviourProfile(
            typing_wpm=rng.randint(40, 95),
            typo_rate=rng.uniform(0.02, 0.08),
            read_speed_ms_per_word=rng.randint(180, 320),
            scroll_pause_variance=rng.uniform(0.2, 0.6),
            mouse_curve_noise=rng.uniform(0.1, 0.4),
            pre_click_hesitation=(rng.randint(150, 400), rng.randint(600, 1400)),
            between_field_pause=(rng.randint(300, 800), rng.randint(1200, 2800)),
            post_submit_wait=(rng.randint(1200, 2000), rng.randint(3000, 5000)),
        )

    async def type_text(self, page, selector: str, text: str):
        """
        Types text character by character with human-like cadence.
        Occasionally introduces and immediately corrects a typo.
        """
        await page.click(selector)

        chars_per_second = (self.profile.typing_wpm * 5) / 60
        base_delay = 1000 / chars_per_second  # ms per character

        for i, char in enumerate(text):
            # Introduce occasional typo
            if random.random() < self.profile.typo_rate and char.isalpha():
                typo_char = random.choice("qwertyuiopasdfghjklzxcvbnm")
                await page.keyboard.type(typo_char)
                await asyncio.sleep(random.uniform(0.08, 0.18))
                await page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.05, 0.12))

            await page.keyboard.type(char)

            # Variable delay — bursts and micro-pauses
            jitter = random.gauss(0, base_delay * 0.3)
            delay = max(20, base_delay + jitter) / 1000
            await asyncio.sleep(delay)

            # Occasional longer pause mid-word (thinking moment)
            if char == " " and random.random() < 0.07:
                await asyncio.sleep(random.uniform(0.3, 0.9))

    async def move_and_click(self, page, selector: str):
        """
        Moves mouse in a natural curve to the element before clicking.
        """
        element = await page.query_selector(selector)
        if not element:
            return
        box = await element.bounding_box()
        if not box:
            return

        target_x = box["x"] + box["width"] / 2 + random.uniform(-4, 4)
        target_y = box["y"] + box["height"] / 2 + random.uniform(-3, 3)

        viewport = page.viewport_size
        start_x = viewport["width"] / 2 + random.uniform(-80, 80)
        start_y = viewport["height"] / 2 + random.uniform(-80, 80)

        # Generate curved path using quadratic Bezier
        steps = random.randint(18, 35)
        ctrl_x = (start_x + target_x) / 2 + random.uniform(-60, 60) * self.profile.mouse_curve_noise
        ctrl_y = (start_y + target_y) / 2 + random.uniform(-60, 60) * self.profile.mouse_curve_noise

        for step in range(steps + 1):
            t = step / steps
            x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * ctrl_x + t ** 2 * target_x
            y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * ctrl_y + t ** 2 * target_y
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.008, 0.022))

        hesitation = random.uniform(*self.profile.pre_click_hesitation) / 1000
        await asyncio.sleep(hesitation)
        await page.mouse.click(target_x, target_y)

    async def click_element(self, page, selector: str):
        """
        Click an element using natural mouse movement.
        Falls back to direct click if element can't be located for movement.
        """
        try:
            await self.move_and_click(page, selector)
        except Exception:
            # Fallback: direct programmatic click
            await page.click(selector)

    async def read_page(self, page):
        """Simulates reading the page by scrolling slowly through it."""
        total_height = await page.evaluate("document.body.scrollHeight")
        viewport_height = page.viewport_size["height"]
        scroll_steps = max(3, total_height // viewport_height)

        for step in range(scroll_steps):
            scroll_y = int((step / scroll_steps) * total_height)
            await page.evaluate(f"window.scrollTo({{top: {scroll_y}, behavior: 'smooth'}})")

            word_count_estimate = random.randint(30, 80)
            read_time = (word_count_estimate * self.profile.read_speed_ms_per_word) / 1000
            variance = read_time * self.profile.scroll_pause_variance
            pause = read_time + random.uniform(-variance, variance)
            await asyncio.sleep(max(0.7, pause))

    async def human_delay(self, min_sec: float, max_sec: float):
        """Generic human delay between min and max seconds."""
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    async def pause_between_fields(self):
        """Short human pause when moving between form fields."""
        delay = random.uniform(*self.profile.between_field_pause) / 1000
        await asyncio.sleep(delay)

    async def pause_after_submit(self):
        """Wait after submitting — humans wait to see confirmation."""
        delay = random.uniform(*self.profile.post_submit_wait) / 1000
        await asyncio.sleep(delay)

    async def handle_interruptions(self, page):
        """
        Scans for and handles common web interruptions like cookie banners,
        popups, or simple confirmation dialogs that block main content.
        """
        interrupt_selectors = [
            "button:has-text('Accept all')", "button:has-text('I agree')",
            "button:has-text('Agree')", "button:has-text('Accept cookies')",
            "button:has-text('OK')", "[aria-label='Accept all']",
            "button:has-text('Reject all')", "button >> text=I agree"
        ]

        # Check for CAPTCHA first as it's the most critical blocking element
        await self.detect_and_solve_captcha(page)

        for selector in interrupt_selectors:
            try:
                btn = await page.wait_for_selector(selector, timeout=1500, state="visible")
                if btn:
                    await self.click_element(page, selector)
                    await asyncio.sleep(1.5)
                    return True
            except Exception:
                continue
        return False

    async def detect_and_solve_captcha(self, page):
        """
        Detects if a reCAPTCHA checkbox is present and attempts to click it.
        """
        try:
            # Look for the internal reCAPTCHA iframe
            frames = page.frames
            captcha_frame = None
            for frame in frames:
                if "recaptcha" in frame.url and "anchor" in frame.url:
                    captcha_frame = frame
                    break
            
            if captcha_frame:
                checkbox = await captcha_frame.wait_for_selector("#recaptcha-anchor", timeout=2000)
                if checkbox:
                    # Clicking inside a frame is tricky; better to use frame.click
                    await checkbox.click()
                    await asyncio.sleep(2)
                    return True
        except Exception:
            pass
        return False

    async def simulate_idle_behavior(self, page):
        """
        Simulates restless human behavior like small mouse twitches or
        minor scroll adjustments during 'thinking' or 'waiting' periods.
        """
        if random.random() < 0.3:
            # Minor mouse twitch
            viewport = page.viewport_size
            cur_x = viewport["width"] / 2
            cur_y = viewport["height"] / 2
            await self.move_to_point(page, cur_x + random.randint(-15, 15), cur_y + random.randint(-15, 15))
        
        if random.random() < 0.2:
            # Minor scroll adjustment
            await page.mouse.wheel(0, random.randint(-100, 100))

    async def move_to_point(self, page, x: float, y: float):
        """Internal helper to move mouse naturally to a coordinate."""
        # Get current mouse position (approximate to viewport center if unknown)
        start_x = page.viewport_size["width"] / 2
        start_y = page.viewport_size["height"] / 2

        steps = random.randint(15, 25)
        ctrl_x = (start_x + x) / 2 + random.uniform(-40, 40)
        ctrl_y = (start_y + y) / 2 + random.uniform(-40, 40)

        for step in range(steps + 1):
            t = step / steps
            path_x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * ctrl_x + t ** 2 * x
            path_y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * ctrl_y + t ** 2 * y
            await page.mouse.move(path_x, path_y)
            await asyncio.sleep(random.uniform(0.01, 0.02))

    async def random_sleep(self, min_s: float, max_s: float):
        """Consistently used randomized sleep."""
        await asyncio.sleep(random.uniform(min_s, max_s))
