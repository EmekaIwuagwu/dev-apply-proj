import asyncio
import random
import logging
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from agent.brain.human_brain import HumanBrain
from agent.browser.form_filler import FormFiller
from typing import List, Any, Dict

logger = logging.getLogger(__name__)

import os
from pathlib import Path

class ExecutePhase:
    def __init__(self, user: Any, planned_jobs: List[Any]):
        self.user = user
        self.planned_jobs = planned_jobs
        self.brain = HumanBrain(personality_seed=str(user.id))
        
        # User-specific browser profile directory
        self.profile_dir = Path(__file__).parent.parent / "browser" / "profiles" / str(user.id)
        os.makedirs(self.profile_dir, exist_ok=True)

    async def execute(self) -> List[Dict[str, Any]]:
        results = []
        async with async_playwright() as p:
            # Persistent context for reputation management
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars"
                ],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            # Mask fingerprint indicators
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
                Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            """)
            
            for job in self.planned_jobs:
                result = await self._apply_to_job(context, job)
                results.append(result)
                
                # Multi-minute rests between applications simulate a real person's pace
                idle_time = random.uniform(45, 120) 
                logger.info(f"Resting for {idle_time:.2f}s to avoid rate-limiting...")
                await asyncio.sleep(idle_time)

            await context.close()
        return results

    async def _apply_to_job(self, context, job: Any) -> Dict[str, Any]:
        page = await context.new_page()
        # Mask automation signatures
        await Stealth().apply_stealth_async(page)
        
        try:
            logger.info(f"Applying to {job.title} at {job.company}...")
            await page.goto(job.url, wait_until="networkidle", timeout=60000)
            
            # Spend time 'reading' the job details
            await self.brain.read_page(page)
            await self.brain.human_delay(2, 5)
            
            # Transition Listing -> Form if necessary (common on Lever/Greenhouse)
            filler = FormFiller(page, self.user, self.brain)
            
            async def get_visible_form():
                elements = await filler._scan_form()
                return elements
            
            form_elements = await get_visible_form()
            
            if not form_elements:
                logger.info(f"No visible form on landing page for {job.company}. Seeking 'Apply' button...")
                apply_selectors = [
                    "a:has-text('Apply for this job')", "button:has-text('Apply for this job')",
                    "a:has-text('Apply Now')", "button:has-text('Apply Now')",
                    "a:has-text('Apply')", "button:has-text('Apply')",
                    ".postings-btn", "a[href*='/apply']"
                ]
                
                found_apply = False
                for s in apply_selectors:
                    if await page.query_selector(s):
                        logger.info(f"Found apply button with selector: {s}")
                        # Direct click fallback if move_and_click is grumpy
                        try:
                            await self.brain.click_element(page, s)
                        except:
                            await page.click(s)
                            
                        logger.info(f"Clicked 'Apply' for {job.company}. Waiting for form transition...")
                        await asyncio.sleep(3)
                        
                        # Wait for form or navigation
                        try:
                            await page.wait_for_load_state("networkidle", timeout=10000)
                        except:
                            pass

                        for _ in range(5):
                            form_elements = await get_visible_form()
                            if form_elements:
                                break
                            await asyncio.sleep(2)
                        
                        found_apply = True
                        break
                
                # Lever-specific direct apply URL hack if still stuck
                if (not form_elements) and "lever.co" in page.url and "/apply" not in page.url:
                    apply_url = page.url.rstrip("/") + "/apply"
                    logger.info(f"Lever portal detected. Trying direct apply URL: {apply_url}")
                    await page.goto(apply_url, wait_until="networkidle")
                    form_elements = await get_visible_form()

                if not form_elements:
                    logger.warning(f"Could not reach visible form for {job.company}.")
                    return {"status": "skipped", "job": job, "error": "Form not found or remained hidden"}

            # Intelligent Fill
            forms = await get_visible_form()
            logger.info(f"Form detected with {len(forms)} visible fields.")
            await filler.fill_all_fields(job)
            
            # Debug: Form filled
            await page.screenshot(path=f"debug_filled_{job.company}.png")
            logger.info(f"Form filled for {job.company}. Debug screenshot saved.")
            
            # CAPTCHA detection check
            if await self.brain.detect_and_solve_captcha(page):
                logger.info(f"reCAPTCHA detected and handled for {job.company}.")
                await asyncio.sleep(2)
            
            # Submit Detection
            submit_selectors = [
                "button:has-text('Submit')", "button:has-text('Apply')",
                "input[type='submit']", "button[type='submit']"
            ]
            
            found_btn = False
            for selector in submit_selectors:
                if await page.query_selector(selector):
                    logger.info(f"Submitting application for {job.company}...")
                    # Human-like click
                    await self.brain.click_element(page, selector)
                    found_btn = True
                    break
            
            if not found_btn:
                return {"status": "skipped", "job": job, "error": "No submit button found"}

            # Wait to see confirmation page
            await self.brain.pause_after_submit()
            await asyncio.sleep(5)
            
            # Debug: After submit attempt
            await page.screenshot(path=f"debug_after_submit_{job.company}.png")
            logger.info(f"After submit attempt for {job.company}. Debug screenshot saved.")
            
            content = (await page.content()).lower()
            if any(x in content for x in ["thank", "received", "success", "confirmed", "submitted"]):
                return {"status": "submitted", "job": job}
            else:
                return {"status": "failed", "job": job, "error": "Success confirmation not detected"}

        except Exception as e:
            logger.error(f"Application crash for {job.company}: {str(e)}")
            return {"status": "failed", "job": job, "error": str(e)}
        finally:
            await page.close()
        
        # Final fallback return
        return {"status": "failed", "job": job, "error": "Unexpected end of execution"}
