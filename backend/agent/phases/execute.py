import asyncio
import logging
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright
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
            on_form = await self._ensure_on_application_form(page, job)
            if not on_form:
                return {
                    "status": "skipped",
                    "job": job,
                    "error": "Could not locate or reach the application form",
                }

            # ---- Multi-page form filling ----
            submitted = await self._fill_and_submit(page, job)
            if not submitted:
                return {
                    "status": "skipped",
                    "job": job,
                    "error": "No submit button found after filling form",
                }

            # ---- Confirm success ----
            await self.brain.pause_after_submit()
            await asyncio.sleep(5)
            await page.screenshot(
                path=f"debug_post_submit_{job.company}.png"
            )

            content = (await page.content()).lower()
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
            await page.close()

    # ------------------------------------------------------------------
    # Navigate from listing → application form
    # ------------------------------------------------------------------

    async def _ensure_on_application_form(self, page, job: Any) -> bool:
        """
        Returns True once the page contains visible form fields.
        Tries apply-button clicks and Lever-style /apply URL hack.
        """
        filler = FormFiller(page, self.user, self.brain, self.preferences)

        if await self._has_visible_form(filler):
            return True

        logger.info(f"No form on landing page for {job.company} — seeking Apply button …")

        for selector in _APPLY_ENTRY_SELECTORS:
            try:
                el = await page.query_selector(selector)
                if not el:
                    continue

                logger.info(f"Clicking apply button: {selector}")
                try:
                    await self.brain.click_element(page, selector)
                except Exception:
                    await page.click(selector)

                await asyncio.sleep(3)
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass

                # Poll for form appearance (up to 10 s)
                for _ in range(5):
                    if await self._has_visible_form(filler):
                        return True
                    await asyncio.sleep(2)

                # Break on first button found even if form not yet visible
                break

            except Exception as e:
                logger.debug(f"Apply selector {selector!r} failed: {e}")

        # Lever-specific direct /apply URL hack
        if not await self._has_visible_form(filler):
            if "lever.co" in page.url and "/apply" not in page.url:
                apply_url = page.url.rstrip("/") + "/apply"
                logger.info(f"Lever portal — trying direct apply URL: {apply_url}")
                await page.goto(apply_url, wait_until="networkidle", timeout=30000)
                if await self._has_visible_form(filler):
                    return True

        return await self._has_visible_form(filler)

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
