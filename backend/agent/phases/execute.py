import asyncio
import logging
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import BrowserContext, Page, async_playwright
from playwright_stealth import Stealth

from agent.brain.human_brain import HumanBrain
from agent.browser.form_filler import FormFiller

logger = logging.getLogger(__name__)

# Buttons that advance a multi-step form to the next page
_NEXT_PAGE_SELECTORS = [
    "button:has-text('Next')",
    "button:has-text('Continue')",
    "button:has-text('Next Step')",
    "button:has-text('Next Page')",
    "button:has-text('Proceed')",
    "input[value='Next']",
    "a:has-text('Next')",
]

# Buttons / inputs that submit the final application
_SUBMIT_SELECTORS = [
    "button:has-text('Submit Application')",
    "button:has-text('Submit')",
    "button:has-text('Apply')",
    "button:has-text('Send Application')",
    "button:has-text('Complete Application')",
    "input[type='submit']",
    "button[type='submit']",
]

# Buttons that open the application form from a job listing page
_APPLY_ENTRY_SELECTORS = [
    "a:has-text('Apply for this job')",
    "button:has-text('Apply for this job')",
    "a:has-text('Apply Now')",
    "button:has-text('Apply Now')",
    "a:has-text('Apply')",
    "button:has-text('Apply')",
    ".postings-btn",
    "a[href*='/apply']",
]

# Keywords that indicate a successful submission confirmation page
_SUCCESS_KEYWORDS = [
    "thank you",
    "thank",
    "received",
    "success",
    "confirmed",
    "submitted",
    "application complete",
    "we'll be in touch",
]


class ExecutePhase:
    def __init__(
        self,
        user: Any,
        planned_jobs: List[Any],
        preferences: Any = None,
    ):
        self.user = user
        self.planned_jobs = planned_jobs
        self.preferences = preferences        # Full JobPreference object
        self.brain = HumanBrain(personality_seed=str(user.id))

        self.profile_dir = (
            Path(__file__).parent.parent / "browser" / "profiles" / str(user.id)
        )
        os.makedirs(self.profile_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def execute(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                ],
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
            )

            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver',
                    {get: () => undefined});
                Object.defineProperty(navigator, 'hardwareConcurrency',
                    {get: () => 8});
                Object.defineProperty(navigator, 'deviceMemory',
                    {get: () => 8});
            """)

            for job in self.planned_jobs:
                result = await self._apply_to_job(context, job)
                results.append(result)

                # Human-paced rest between applications
                idle = random.uniform(45, 120)
                logger.info(f"Resting {idle:.1f}s before next application …")
                await asyncio.sleep(idle)

            await context.close()

        return results

    # ------------------------------------------------------------------
    # Per-job application
    # ------------------------------------------------------------------

    async def _apply_to_job(self, context, job: Any) -> Dict[str, Any]:
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        try:
            logger.info(f"Navigating to listing: {job.title} @ {job.company}")
            await page.goto(job.url, wait_until="networkidle", timeout=60000)
            await self.brain.read_page(page)
            await self.brain.human_delay(2, 5)
            await self.brain.handle_interruptions(page)

            # ---- Try to reach the application form ----
            form_page = await self._ensure_on_application_form(context, page, job)
            if not form_page:
                return {
                    "status": "skipped",
                    "job": job,
                    "error": "Could not locate or reach the application form",
                }

            # ---- Multi-page form filling (use form_page — may differ from page) ----
            submitted = await self._fill_and_submit(form_page, job)
            if not submitted:
                return {
                    "status": "skipped",
                    "job": job,
                    "error": "No submit button found after filling form",
                }

            # ---- Confirm success ----
            await self.brain.pause_after_submit()
            await asyncio.sleep(5)
            await form_page.screenshot(
                path=f"debug_post_submit_{job.company}.png"
            )

            content = (await form_page.content()).lower()
            if any(kw in content for kw in _SUCCESS_KEYWORDS):
                logger.info(f"Application submitted: {job.title} @ {job.company}")
                return {"status": "submitted", "job": job}

            return {
                "status": "failed",
                "job": job,
                "error": "Success confirmation not detected on final page",
            }

        except Exception as e:
            logger.error(f"Application crashed for {job.company}: {e}")
            return {"status": "failed", "job": job, "error": str(e)}
        finally:
            try:
                await page.close()
            except Exception:
                pass
            # If the form was on a different tab, close that too
            try:
                if form_page is not None and form_page != page:
                    await form_page.close()
            except (NameError, Exception):
                pass

    # ------------------------------------------------------------------
    # Navigate from listing → application form
    # ------------------------------------------------------------------

    async def _ensure_on_application_form(
        self, context: BrowserContext, page: Page, job: Any
    ) -> Optional[Page]:
        """
        Navigates to the application form and returns the Page that contains it.
        Returns None if the form cannot be reached.

        Handles three scenarios:
          1. Form already visible on the landing page.
          2. Apply button click navigates the same tab to a form page.
          3. Apply button click opens a NEW tab — we switch to that tab.
        Includes Lever and Ashby URL fallbacks as a last resort.
        """
        filler = FormFiller(page, self.user, self.brain, self.preferences)

        if await self._has_visible_form(filler):
            return page

        logger.info(f"No form on landing page for {job.company} — seeking Apply button …")

        for selector in _APPLY_ENTRY_SELECTORS:
            try:
                el = await page.query_selector(selector)
                if not el:
                    continue

                logger.info(f"Clicking apply button: {selector}")

                # Record existing pages before click so we can detect new tabs
                pages_before = set(context.pages)

                try:
                    await self.brain.click_element(page, selector)
                except Exception:
                    try:
                        await page.click(selector)
                    except Exception:
                        continue  # Can't click — try next selector

                # Brief wait for navigation / new tab to appear
                await asyncio.sleep(2)

                # Check if a new tab was opened
                new_pages = [p for p in context.pages if p not in pages_before and not p.is_closed()]
                if new_pages:
                    new_tab: Page = new_pages[-1]
                    try:
                        await new_tab.wait_for_load_state("networkidle", timeout=15000)
                    except Exception:
                        pass
                    await Stealth().apply_stealth_async(new_tab)
                    logger.info(f"Apply button opened new tab: {new_tab.url}")
                    new_filler = FormFiller(new_tab, self.user, self.brain, self.preferences)
                    for _ in range(5):
                        if await self._has_visible_form(new_filler):
                            return new_tab
                        await asyncio.sleep(2)
                    # New tab opened but no form; close and try next selector
                    await new_tab.close()
                    continue

                # Same-tab navigation — wait for load and poll for form
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass

                for _ in range(5):
                    if await self._has_visible_form(filler):
                        return page
                    await asyncio.sleep(2)

                # No form found — continue to next selector

            except Exception as e:
                logger.debug(f"Apply selector {selector!r} failed: {e}")

        # ---- ATS-specific direct /apply URL fallbacks ----
        current_url = page.url

        if "lever.co" in current_url and "/apply" not in current_url:
            apply_url = current_url.rstrip("/") + "/apply"
            logger.info(f"Lever portal — trying direct apply URL: {apply_url}")
            await page.goto(apply_url, wait_until="networkidle", timeout=30000)
            if await self._has_visible_form(filler):
                return page

        if "ashbyhq.com" in current_url and "/apply" not in current_url:
            apply_url = current_url.rstrip("/") + "/apply"
            logger.info(f"Ashby portal — trying direct apply URL: {apply_url}")
            await page.goto(apply_url, wait_until="networkidle", timeout=30000)
            if await self._has_visible_form(filler):
                return page

        return None if not await self._has_visible_form(filler) else page

    # ------------------------------------------------------------------
    # Multi-page form fill + final submit
    # ------------------------------------------------------------------

    async def _fill_and_submit(self, page, job: Any) -> bool:
        """
        Fills the current form page, advances through Next/Continue buttons,
        and ultimately clicks the Submit button on the final page.
        Returns True if a submit button was found and clicked.
        """
        max_pages = 6

        for page_num in range(max_pages):
            logger.info(f"Filling form page {page_num + 1} for {job.company} …")

            filler = FormFiller(page, self.user, self.brain, self.preferences)
            await filler.fill_all_fields(job)

            await page.screenshot(
                path=f"debug_filled_p{page_num + 1}_{job.company}.png"
            )

            # CAPTCHA check after each fill
            if await self.brain.detect_and_solve_captcha(page):
                logger.info("CAPTCHA handled.")
                await asyncio.sleep(2)

            # Check for a Next / Continue button first
            next_sel = await self._find_selector(page, _NEXT_PAGE_SELECTORS)
            if next_sel:
                logger.info(f"Multi-step form — clicking Next (page {page_num + 1})")
                await self.brain.click_element(page, next_sel)
                await asyncio.sleep(3)
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                continue  # Fill next page

            # No Next button — look for Submit
            submit_sel = await self._find_selector(page, _SUBMIT_SELECTORS)
            if submit_sel:
                logger.info(f"Submitting application for {job.company} …")
                await self.brain.click_element(page, submit_sel)
                return True

            # Neither Next nor Submit found — bail
            logger.warning(
                f"No Next or Submit button found on page {page_num + 1} "
                f"for {job.company}."
            )
            return False

        # Hit page limit without finding Submit
        logger.warning(f"Reached max page limit for {job.company} form.")
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _has_visible_form(self, filler: FormFiller) -> bool:
        elements = await filler._scan_form()
        return bool(elements)

    @staticmethod
    async def _find_selector(page, selectors: List[str]) -> Optional[str]:
        """Return the first selector that matches a visible element, or None."""
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    return sel
            except Exception:
                pass
        return None
