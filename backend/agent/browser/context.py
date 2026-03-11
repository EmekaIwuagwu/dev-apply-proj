"""
context.py — Create a stealth Playwright browser context.

Settings that make us look human:
  - Consistent, realistic user-agent string
  - Realistic viewport
  - Disabled automation flags
  - Navigator.webdriver property spoofed to undefined
  - Persistent profile directory per user (cookies, localStorage survive)
"""
import logging
import os

from playwright.async_api import BrowserContext, Playwright
from playwright_stealth import Stealth

from agent.vision.screen import VIEWPORT

logger = logging.getLogger(__name__)


async def new_context(p: Playwright, profile_dir: str) -> BrowserContext:
    """
    Launch a persistent Chromium context for one user.

    profile_dir — user-specific directory so cookies / sessions persist
                  across daily runs.
    """
    os.makedirs(profile_dir, exist_ok=True)

    ctx: BrowserContext = await p.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        headless=True,  # headless: screenshots still work; no display needed
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--disable-extensions",
            "--disable-gpu",
            "--window-size=1366,768",
        ],
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport=VIEWPORT,
        locale="en-US",
        timezone_id="America/New_York",
        color_scheme="light",
        ignore_https_errors=False,
    )

    # Overwrite `navigator.webdriver` on every page that opens
    await ctx.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    """)

    logger.info(f"Browser context created: {profile_dir}")
    return ctx


async def new_stealth_page(ctx: BrowserContext):
    """Open a new page inside the context with stealth applied."""
    page = await ctx.new_page()
    await Stealth().apply_stealth_async(page)
    return page
