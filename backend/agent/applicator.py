"""
Applicator — opens the application form for a single job and submits it.

Strategy (in order of reliability):
  1. Navigate directly to the /apply URL (works for Lever always, often Ashby).
  2. If no form found, go to the listing page and click the Apply button.
  3. If the Apply click opens a new tab, switch to it.
  4. Fill every visible form field (LLM-guided + human-like typing).
  5. Handle multi-page forms (Next / Continue buttons).
  6. Click Submit and check the confirmation page for success keywords.
"""
import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

from playwright.async_api import BrowserContext, Page, async_playwright
from playwright_stealth import Stealth

from agent.brain import Brain
from agent.filler import FormFiller
from agent.planner import PlannedJob

logger = logging.getLogger(__name__)

# Selectors tried (in order) when looking for the Apply entry button
_APPLY_BTNS = [
    "button:has-text('Apply for this job')",
    "a:has-text('Apply for this job')",
    "button:has-text('Apply Now')",
    "a:has-text('Apply Now')",
    "button:has-text('Apply')",
    "a:has-text('Apply')",
    ".postings-btn",
]

# Selectors for Next / Continue in multi-page forms
_NEXT_BTNS = [
    "button:has-text('Next')",
    "button:has-text('Continue')",
    "button:has-text('Next Step')",
    "input[value='Next']",
    "a:has-text('Next')",
]

# Final submit button selectors
_SUBMIT_BTNS = [
    "button:has-text('Submit Application')",
    "button:has-text('Submit')",
    "input[type='submit']",
    "button[type='submit']",
    "button:has-text('Send Application')",
    "button:has-text('Complete Application')",
]

# Keywords on the confirmation page that mean success
_SUCCESS = [
    "thank you", "thanks", "application received", "successfully submitted",
    "application complete", "we'll be in touch", "we will be in touch",
    "application submitted", "received your application",
]


@dataclass
class ApplyResult:
    status: str          # "submitted" | "skipped" | "failed"
    error: Optional[str] = None


class Applicator:
    def __init__(self, user: Any, preferences: Any, profile_dir: str):
        self.user = user
        self.preferences = preferences
        self.profile_dir = profile_dir
        self.brain = Brain(seed=str(user.id))

    # ------------------------------------------------------------------
    # Public entry: apply to a list of jobs and return per-job results
    # ------------------------------------------------------------------

    async def run(self, jobs: List[PlannedJob]) -> List[dict]:
        results = []
        async with async_playwright() as p:
            context = await self._make_context(p)
            try:
                for job in jobs:
                    logger.info(f"Applying: {job.title} @ {job.company} — {job.url}")
                    result = await self._apply_one(context, job)
                    results.append({"job": job, **result.__dict__})
                    # Human-paced gap between applications
                    if jobs.index(job) < len(jobs) - 1:
                        await self.brain.sleep(30, 90)
            finally:
                await context.close()
        return results

    # ------------------------------------------------------------------
    # Apply to a single job
    # ------------------------------------------------------------------

    async def _apply_one(self, context: BrowserContext, job: PlannedJob) -> ApplyResult:
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        form_page: Optional[Page] = None

        try:
            # Step 1 — find the application form page
            form_page = await self._reach_form(context, page, job)
            if form_page is None:
                return ApplyResult("skipped", "Could not reach the application form")

            # Step 2 — fill + submit (handles multi-page forms)
            submitted = await self._fill_and_submit(form_page, job)
            if not submitted:
                return ApplyResult("skipped", "No submit button found after filling form")

            # Step 3 — confirm success
            await self.brain.after_submit()
            await asyncio.sleep(3)

            content = (await form_page.content()).lower()
            if any(kw in content for kw in _SUCCESS):
                logger.info(f"Submitted: {job.title} @ {job.company}")
                return ApplyResult("submitted")

            # Take a screenshot for debugging
            try:
                await form_page.screenshot(path=f"/tmp/debug_{job.company}.png")
            except Exception:
                pass

            return ApplyResult("failed", "Success confirmation not detected")

        except Exception as e:
            logger.error(f"Application crashed for {job.company}: {e}", exc_info=True)
            return ApplyResult("failed", str(e))

        finally:
            try:
                await page.close()
            except Exception:
                pass
            try:
                if form_page and form_page != page:
                    await form_page.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Reach the application form
    # ------------------------------------------------------------------

    async def _reach_form(
        self, context: BrowserContext, page: Page, job: PlannedJob
    ) -> Optional[Page]:
        """
        Returns the Page that contains the application form, or None.

        Order of attempts:
          A. Direct /apply URL (most reliable for Lever, works on many Ashby jobs)
          B. Load listing page → click Apply button (same-tab or new-tab)
          C. Direct /application URL (Ashby variant)
        """

        # ---- Attempt A: direct /apply URL ----
        apply_url = self._direct_apply_url(job.url)
        if apply_url != job.url:
            logger.info(f"Trying direct apply URL: {apply_url}")
            try:
                await page.goto(apply_url, wait_until="domcontentloaded", timeout=25000)
                await asyncio.sleep(2)
                await self.brain.dismiss_interruptions(page)
                if await self._has_form(page):
                    logger.info("Form found via direct /apply URL")
                    return page
            except Exception as e:
                logger.debug(f"Direct /apply failed: {e}")

        # ---- Attempt B: listing page + click Apply button ----
        logger.info(f"Loading listing page: {job.url}")
        try:
            await page.goto(job.url, wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(2)
            await self.brain.dismiss_interruptions(page)
            await self.brain.read_page(page)
        except Exception as e:
            logger.warning(f"Could not load listing page: {e}")
            return None

        # If the listing page itself already has a form (some Ashby inline forms)
        if await self._has_form(page):
            logger.info("Form found directly on listing page")
            return page

        # Try each Apply button
        for sel in _APPLY_BTNS:
            el = await page.query_selector(sel)
            if not el:
                continue

            logger.info(f"Clicking: {sel}")
            pages_before = set(context.pages)

            try:
                await self.brain.click(page, sel)
            except Exception:
                try:
                    await page.click(sel, timeout=5000)
                except Exception:
                    continue

            await asyncio.sleep(2)

            # Check for new tab
            new_tabs = [p for p in context.pages if p not in pages_before and not p.is_closed()]
            if new_tabs:
                new_tab = new_tabs[-1]
                try:
                    await new_tab.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    pass
                await Stealth().apply_stealth_async(new_tab)
                await asyncio.sleep(2)
                logger.info(f"New tab opened: {new_tab.url}")
                if await self._has_form(new_tab):
                    logger.info("Form found in new tab")
                    return new_tab
                await new_tab.close()
                continue

            # Same-tab navigation
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass

            # Poll up to 12 seconds for the form to appear
            for _ in range(6):
                if await self._has_form(page):
                    logger.info("Form found after clicking Apply button")
                    return page
                await asyncio.sleep(2)

        # ---- Attempt C: direct /application URL (Ashby variant) ----
        if "ashbyhq.com" in job.url:
            app_url = job.url.rstrip("/") + "/application"
            logger.info(f"Trying Ashby /application URL: {app_url}")
            try:
                await page.goto(app_url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(2)
                if await self._has_form(page):
                    logger.info("Form found via /application URL")
                    return page
            except Exception as e:
                logger.debug(f"/application URL failed: {e}")

        logger.warning(f"Could not reach application form for {job.company}")
        return None

    # ------------------------------------------------------------------
    # Fill form and submit
    # ------------------------------------------------------------------

    async def _fill_and_submit(self, page: Page, job: PlannedJob) -> bool:
        """
        Fill the current form page.  If a Next/Continue button exists, click it
        and fill the next page.  When we find Submit, click it and return True.
        Max 8 pages before giving up.
        """
        for page_num in range(8):
            logger.info(f"Filling form page {page_num + 1} for {job.company}")

            filler = FormFiller(page, self.user, self.brain, self.preferences)
            await filler.fill(job)

            # Check for Next button (multi-step form)
            next_sel = await self._find_btn(page, _NEXT_BTNS)
            if next_sel:
                logger.info(f"Multi-step: clicking Next (page {page_num + 1})")
                await self.brain.click(page, next_sel)
                await asyncio.sleep(3)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                except Exception:
                    pass
                continue  # fill next page

            # Look for Submit
            submit_sel = await self._find_btn(page, _SUBMIT_BTNS)
            if submit_sel:
                logger.info(f"Clicking Submit for {job.company}")
                await self.brain.click(page, submit_sel)
                return True

            logger.warning(f"No Next or Submit on page {page_num + 1} for {job.company}")
            return False

        logger.warning(f"Exceeded max pages for {job.company}")
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _has_form(self, page: Page) -> bool:
        """
        Return True if the page has at least 2 visible, fillable form fields.
        This avoids false positives from stray <input> elements (e.g. nav search).
        """
        try:
            count = await page.evaluate("""
                () => document.querySelectorAll('input, textarea, select')
                    .length > 0
                    ? Array.from(document.querySelectorAll('input, textarea, select'))
                        .filter(el => {
                            const s = window.getComputedStyle(el);
                            const b = el.getBoundingClientRect();
                            return (
                                s.display !== 'none' &&
                                s.visibility !== 'hidden' &&
                                el.type !== 'hidden' &&
                                b.width > 0 && b.height > 0
                            );
                        }).length
                    : 0
            """)
            return count >= 2
        except Exception:
            return False

    @staticmethod
    async def _find_btn(page: Page, selectors: List[str]) -> Optional[str]:
        """Return the first matching visible button selector, or None."""
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    return sel
            except Exception:
                pass
        return None

    def _direct_apply_url(self, url: str) -> str:
        """
        Return the direct apply page URL for known ATS portals.
        Returns the original URL unchanged if we don't recognise the portal.
        """
        base = url.rstrip("/")
        # Lever: jobs.lever.co/company/uuid → jobs.lever.co/company/uuid/apply
        if "jobs.lever.co" in url and "/apply" not in url:
            return base + "/apply"
        # Ashby: jobs.ashbyhq.com/company/uuid → jobs.ashbyhq.com/company/uuid/apply
        if "jobs.ashbyhq.com" in url and "/apply" not in url:
            return base + "/apply"
        return url

    async def _make_context(self, p) -> BrowserContext:
        os.makedirs(self.profile_dir, exist_ok=True)
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=self.profile_dir,
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
            ],
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
        )
        await ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        return ctx
