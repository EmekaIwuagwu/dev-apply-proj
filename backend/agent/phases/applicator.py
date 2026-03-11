"""
applicator.py — Phase 3: Fill and submit the job application.

This is the heart of the agent.  It behaves EXACTLY like a human:

  1.  Navigate to the job listing page (already verified in reader phase)
  2.  Scroll through — "re-reading" the posting
  3.  AI Eye LOOKS at the page: find the Apply button visually
  4.  OpenCV confirms there is an interactive region near that coordinate
  5.  HumanMouse moves the cursor in a Bézier curve to the button
  6.  Click — Playwright fires the actual click event
  7.  Wait for the application form to load (new page or same page)
  8.  Screenshot → AI Eye maps every form field (label, type, position)
  9.  For each field:
        a. HumanMouse moves to the field
        b. Click to focus
        c. HumanTypist types the value character-by-character
        d. File inputs: set_input_files() — direct API (no mouse needed)
        e. Select dropdowns: select_option()
        f. Checkboxes: check()
        g. Open-ended questions → AI Eye generates a first-person answer
  10. Find the Submit / Next button via AI Eye
  11. HumanMouse moves to it, pauses (human hesitation), clicks
  12. Multi-page forms: repeat 8-11 up to 8 times
  13. Wait for confirmation page, AI Eye verifies success
"""
import asyncio
import base64
import logging
import os
import random
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from playwright.async_api import BrowserContext, Page

from agent.browser.context import new_stealth_page
from agent.browser.mouse import HumanMouse
from agent.browser.typist import HumanTypist
from agent.phases.reader import EvaluatedJob, _build_profile_text, _dismiss_banners
from agent.vision.ai_eye import AIEye
from agent.vision.detector import find_buttons
from agent.vision.screen import capture

logger = logging.getLogger(__name__)


@dataclass
class ApplyResult:
    status: str          # "submitted" | "skipped" | "failed"
    error: Optional[str] = None


# Button descriptions tried in order when looking for the Apply entry point
_APPLY_BUTTON_DESCRIPTIONS = [
    "the primary green or blue 'Apply' or 'Apply for this job' button",
    "a button labelled Apply Now or Apply for this position",
    "any call-to-action button for applying to this job",
]

# Button descriptions for Next / Continue in multi-step forms
_NEXT_BUTTON_DESCRIPTIONS = [
    "a Next or Continue button to go to the next step of the form",
    "a button labelled Next Step or Proceed",
]

# Button descriptions for the final Submit
_SUBMIT_BUTTON_DESCRIPTIONS = [
    "the final Submit Application or Submit button",
    "a button labelled Submit or Send Application or Complete Application",
    "the primary submit button at the bottom of the application form",
]


async def apply_to_jobs(
    ctx: BrowserContext,
    jobs: List[EvaluatedJob],
    user: Any,
    preferences: Any,
    eye: AIEye,
    seed: str,
) -> List[dict]:
    """
    Apply to each job in sequence.
    Returns a list of {job, status, error} dicts.
    """
    results = []
    profile_text = _build_profile_text(user, preferences)

    for i, job in enumerate(jobs):
        logger.info(f"Applying [{i+1}/{len(jobs)}]: {job.title} @ {job.company}")
        result = await _apply_one(ctx, job, user, preferences, profile_text, eye, seed)
        results.append({"job": job, **result.__dict__})

        # Human pacing — don't hammer the site
        if i < len(jobs) - 1:
            await asyncio.sleep(random.uniform(25, 60))

    return results


# ---------------------------------------------------------------------------
# Single job application
# ---------------------------------------------------------------------------

async def _apply_one(
    ctx: BrowserContext,
    job: EvaluatedJob,
    user: Any,
    preferences: Any,
    profile_text: str,
    eye: AIEye,
    seed: str,
) -> ApplyResult:
    page = await new_stealth_page(ctx)
    mouse = HumanMouse(page, seed=seed)
    typist = HumanTypist(page, seed=seed)
    form_page: Optional[Page] = None

    try:
        # ----------------------------------------------------------------
        # Step 1 — Load the job listing page
        # ----------------------------------------------------------------
        logger.info(f"Loading job page: {job.url}")
        await page.goto(job.url, wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(random.uniform(2, 3.5))
        await _dismiss_banners(page)

        # Re-read the page (human always scrolls before clicking Apply)
        await _human_read_page(page, mouse)

        # ----------------------------------------------------------------
        # Step 2 — Find the Apply button VISUALLY
        # ----------------------------------------------------------------
        form_page = await _find_and_click_apply(page, ctx, mouse, eye, job, seed)
        if form_page is None:
            return ApplyResult("skipped", "Could not locate the Apply button")

        # ----------------------------------------------------------------
        # Step 3 — Fill and submit the form (handles multi-page)
        # ----------------------------------------------------------------
        submitted = await _fill_and_submit(
            form_page, mouse, typist, eye, user, preferences, profile_text, job
        )
        if not submitted:
            return ApplyResult("skipped", "No submit button found or form fill failed")

        # ----------------------------------------------------------------
        # Step 4 — Verify success visually
        # ----------------------------------------------------------------
        await asyncio.sleep(random.uniform(2.5, 4.5))
        raw, bgr, pil = await capture(form_page)

        if await eye.is_success_page(pil):
            logger.info(f"SUCCESS: {job.title} @ {job.company}")
            return ApplyResult("submitted")

        # Fallback text check
        content = (await form_page.content()).lower()
        success_words = ["thank you", "application received", "successfully submitted",
                         "we'll be in touch", "application complete"]
        if any(w in content for w in success_words):
            logger.info(f"SUCCESS (text match): {job.title} @ {job.company}")
            return ApplyResult("submitted")

        logger.warning(f"Submitted but could not confirm success: {job.url}")
        return ApplyResult("failed", "Submission may have succeeded but confirmation not detected")

    except Exception as e:
        logger.error(f"apply_one crashed for {job.company}: {e}", exc_info=True)
        return ApplyResult("failed", str(e))
    finally:
        try:
            await page.close()
        except Exception:
            pass
        try:
            if form_page and form_page != page and not form_page.is_closed():
                await form_page.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Step 2: Find and click Apply
# ---------------------------------------------------------------------------

async def _find_and_click_apply(
    page: Page,
    ctx: BrowserContext,
    mouse: HumanMouse,
    eye: AIEye,
    job: EvaluatedJob,
    seed: str,
) -> Optional[Page]:
    """
    Visually locate the Apply button, click it.
    Returns the page that contains the application form (may be a new tab).
    """
    url = job.url

    # -- Try direct /apply URL first (Lever is always at listing/apply)
    direct_apply_url = _direct_apply_url(url)
    if direct_apply_url != url:
        logger.info(f"Attempting direct /apply URL: {direct_apply_url}")
        await page.goto(direct_apply_url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)
        raw, bgr, pil = await capture(page)
        if await _page_has_form(page):
            logger.info("Form found at direct /apply URL")
            return page
        # Revert to listing page
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(1.5)

    # -- Visually find the Apply button
    for description in _APPLY_BUTTON_DESCRIPTIONS:
        raw, bgr, pil = await capture(page)
        pos = await eye.find_element(pil, description)

        if pos and pos.get("confidence") in ("high", "medium"):
            logger.info(f"AI Eye found Apply button at ({pos['x']}, {pos['y']}) [{pos['confidence']}]")

            # Cross-check with OpenCV: is there a button-like region near that coordinate?
            buttons = find_buttons(bgr)
            nearby = [
                b for b in buttons
                if abs(b["cx"] - pos["x"]) < 80 and abs(b["cy"] - pos["y"]) < 50
            ]
            if nearby:
                # Refine to OpenCV-detected centre for sub-pixel accuracy
                b = min(nearby, key=lambda b: (b["cx"] - pos["x"])**2 + (b["cy"] - pos["y"])**2)
                pos["x"], pos["y"] = b["cx"], b["cy"]
                logger.info(f"OpenCV refined Apply button to ({pos['x']}, {pos['y']})")

            # Scroll button into view
            await mouse.scroll_to_element(pos["x"], pos["y"])
            await asyncio.sleep(random.uniform(0.4, 0.9))

            # Human hesitation before clicking Apply
            await asyncio.sleep(random.uniform(0.8, 2.0))

            pages_before = set(p for p in ctx.pages if not p.is_closed())
            await mouse.click(pos["x"], pos["y"])
            await asyncio.sleep(random.uniform(1.5, 3.0))

            # Check for new tab
            new_tabs = [p for p in ctx.pages if p not in pages_before and not p.is_closed()]
            if new_tabs:
                new_tab = new_tabs[-1]
                try:
                    await new_tab.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    pass
                await asyncio.sleep(2)
                logger.info(f"New tab opened: {new_tab.url}")
                if await _page_has_form(new_tab):
                    return new_tab
                await new_tab.close()
                continue

            # Same-page navigation
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass

            # Poll for form appearing (SPA-style)
            for _ in range(6):
                if await _page_has_form(page):
                    logger.info("Application form appeared after clicking Apply")
                    return page
                await asyncio.sleep(2)

    # -- Last resort: Ashby /application URL
    if "ashbyhq.com" in url:
        app_url = url.rstrip("/") + "/application"
        logger.info(f"Trying Ashby /application fallback: {app_url}")
        await page.goto(app_url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)
        if await _page_has_form(page):
            return page

    logger.warning(f"Could not reach application form for {job.company}")
    return None


# ---------------------------------------------------------------------------
# Step 3: Fill and submit (multi-page capable)
# ---------------------------------------------------------------------------

async def _fill_and_submit(
    page: Page,
    mouse: HumanMouse,
    typist: HumanTypist,
    eye: AIEye,
    user: Any,
    preferences: Any,
    profile_text: str,
    job: EvaluatedJob,
) -> bool:
    """
    Fill every visible form field, handle Next/Continue buttons for
    multi-step forms, then click Submit.  Returns True if Submit was clicked.
    """
    for form_page_num in range(8):
        logger.info(f"Filling form page {form_page_num + 1} for {job.company}")

        # Capture what we see
        raw, bgr, pil = await capture(page)

        # AI Eye maps all visible form fields
        fields = await eye.analyze_form(pil)
        logger.info(f"AI Eye identified {len(fields)} field(s) on form page {form_page_num + 1}")

        # Fill each field
        for field_info in fields:
            await _fill_field(page, mouse, typist, eye, user, preferences, profile_text, field_info, job)
            await asyncio.sleep(random.uniform(0.4, 1.0))

        # Re-capture after filling to find Next/Submit
        raw, bgr, pil = await capture(page)

        # Check for Next button first (multi-step form)
        next_pos = await _find_button(pil, eye, _NEXT_BUTTON_DESCRIPTIONS)
        if next_pos:
            logger.info(f"Multi-step: clicking Next on page {form_page_num + 1}")
            await mouse.scroll_to_element(next_pos["x"], next_pos["y"])
            await asyncio.sleep(random.uniform(0.5, 1.2))
            await mouse.click(next_pos["x"], next_pos["y"])
            await asyncio.sleep(random.uniform(2, 3.5))
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
            continue  # Fill next page

        # Check for Submit button
        submit_pos = await _find_button(pil, eye, _SUBMIT_BUTTON_DESCRIPTIONS)
        if submit_pos:
            logger.info(f"Clicking Submit for {job.company}")
            await mouse.scroll_to_element(submit_pos["x"], submit_pos["y"])
            # Human hesitation before final submit
            await asyncio.sleep(random.uniform(1.5, 3.5))
            await mouse.click(submit_pos["x"], submit_pos["y"])
            return True

        logger.warning(f"No Next or Submit found on form page {form_page_num + 1}")
        return False

    logger.warning(f"Exceeded max form pages for {job.company}")
    return False


# ---------------------------------------------------------------------------
# Field-level filling
# ---------------------------------------------------------------------------

async def _fill_field(
    page: Page,
    mouse: HumanMouse,
    typist: HumanTypist,
    eye: AIEye,
    user: Any,
    preferences: Any,
    profile_text: str,
    field_info: dict,
    job: EvaluatedJob,
) -> None:
    """
    Fill a single form field based on AI Eye field descriptor.

    field_info keys: label, type, x_pct, y_pct, required
    """
    from agent.vision.screen import VIEWPORT_W, VIEWPORT_H

    label = field_info.get("label", "").strip()
    ftype = (field_info.get("type") or "text").lower()
    x = int(field_info.get("x_pct", 0.5) * VIEWPORT_W)
    y = int(field_info.get("y_pct", 0.5) * VIEWPORT_H)

    logger.debug(f"  Field: {label!r} [{ftype}] at ({x}, {y})")

    # Determine what value to fill
    value = _resolve_value(label, ftype, user, preferences, job)

    try:
        if ftype == "file":
            await _upload_resume(page, x, y, user)
            return

        if ftype == "select":
            if value:
                await _select_option(page, x, y, value)
            return

        if ftype == "checkbox":
            # Only check consent/agreement checkboxes
            if any(k in label.lower() for k in ("agree", "consent", "terms", "accept")):
                await _check_box(page, x, y)
            return

        # text / email / tel / url / textarea
        if not value:
            # Open-ended question — generate a first-person answer
            raw, bgr, pil = await capture(page)
            value = await eye.generate_answer(pil, label, profile_text, job.title, job.company)

        if not value:
            return

        # Click the field
        await mouse.click(x, y)
        await asyncio.sleep(random.uniform(0.2, 0.5))

        # Clear any pre-filled content
        await page.keyboard.press("Control+a")
        await asyncio.sleep(0.05)
        await page.keyboard.press("Delete")
        await asyncio.sleep(0.05)

        # Type the value
        if ftype in ("email", "tel", "url") or len(value) < 30:
            await typist.type_fast(value)
        else:
            await typist.type(value)

        await asyncio.sleep(random.uniform(0.1, 0.3))

        # Tab away to trigger validation
        await typist.press("Tab")

    except Exception as e:
        logger.warning(f"fill_field failed for {label!r}: {e}")
        # Last-resort DOM fallback
        try:
            await page.evaluate(
                f"""
                (() => {{
                    const el = document.elementFromPoint({x}, {y});
                    if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {{
                        el.focus();
                        el.value = {repr(value or '')};
                        el.dispatchEvent(new Event('input', {{bubbles: true}}));
                        el.dispatchEvent(new Event('change', {{bubbles: true}}));
                    }}
                }})()
                """
            )
        except Exception:
            pass


def _resolve_value(
    label: str,
    ftype: str,
    user: Any,
    preferences: Any,
    job: EvaluatedJob,
) -> Optional[str]:
    """
    Map a field label to the user's data.
    Returns None for open-ended questions (AI will answer those).
    """
    full_name = getattr(user, "full_name", "") or ""
    parts = full_name.split(" ", 1)
    first = parts[0]
    last = parts[1] if len(parts) > 1 else ""

    label_l = label.lower()

    # Standard field mappings
    mapping = {
        ("full name", "name", "your name", "applicant name"): full_name,
        ("first name", "given name", "firstname"):            first,
        ("last name", "surname", "family name", "lastname"):  last,
        ("email", "e-mail", "email address"):                 getattr(user, "email", ""),
        ("phone", "telephone", "mobile", "cell", "contact number"): getattr(user, "telephone", ""),
        ("linkedin", "linkedin url", "linkedin profile"):     getattr(user, "linkedin_url", ""),
        ("website", "portfolio", "personal site"):            getattr(user, "linkedin_url", ""),
        ("location", "city", "current location", "where are you"):
            (list(getattr(preferences, "preferred_locations", []) or []) + ["Remote"])[0]
            if preferences else "Remote",
    }

    for keys, val in mapping.items():
        if any(k in label_l for k in keys):
            return val or None

    # File and select types handled upstream
    if ftype == "file":
        return None

    # Everything else is open-ended → return None to trigger AI generation
    return None


async def _upload_resume(page: Page, x: int, y: int, user: Any) -> None:
    b64 = getattr(user, "resume_base64", "") or ""
    if not b64:
        logger.warning("No resume on user profile — skipping upload")
        return

    filename = getattr(user, "resume_filename", None) or f"resume_{user.id}.pdf"
    tmp_path = os.path.join(tempfile.gettempdir(), filename)

    try:
        with open(tmp_path, "wb") as fh:
            fh.write(base64.b64decode(b64))

        # Use Playwright's set_input_files — finds the nearest file input to coords
        file_inputs = await page.query_selector_all("input[type='file']")
        if file_inputs:
            await file_inputs[0].set_input_files(tmp_path)
            logger.info(f"Resume uploaded: {filename}")
        else:
            logger.warning("No file input found on page")
    except Exception as e:
        logger.error(f"Resume upload error: {e}")


async def _select_option(page: Page, x: int, y: int, value: str) -> None:
    try:
        el = await page.evaluate_handle(f"document.elementFromPoint({x}, {y})")
        tag = await page.evaluate("el => el.tagName", el)
        if tag == "SELECT":
            await page.evaluate(
                f"""
                (el) => {{
                    const opts = Array.from(el.options);
                    const match = opts.find(o =>
                        o.text.toLowerCase().includes({repr(value.lower())}) ||
                        o.value.toLowerCase().includes({repr(value.lower())})
                    );
                    if (match) {{
                        el.value = match.value;
                        el.dispatchEvent(new Event('change', {{bubbles: true}}));
                    }}
                }}
                """,
                el,
            )
    except Exception as e:
        logger.debug(f"select_option failed: {e}")


async def _check_box(page: Page, x: int, y: int) -> None:
    try:
        el = await page.evaluate_handle(f"document.elementFromPoint({x}, {y})")
        await page.evaluate(
            "(el) => { if (el && !el.checked) el.click(); }",
            el,
        )
    except Exception as e:
        logger.debug(f"check_box failed: {e}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _page_has_form(page: Page) -> bool:
    """True if the page has ≥ 2 visible fillable form fields."""
    try:
        count = await page.evaluate("""
            () => Array.from(document.querySelectorAll('input,textarea,select'))
                .filter(el => {
                    const s = window.getComputedStyle(el);
                    const b = el.getBoundingClientRect();
                    return s.display !== 'none' && s.visibility !== 'hidden'
                        && el.type !== 'hidden' && b.width > 0 && b.height > 0;
                }).length
        """)
        return count >= 2
    except Exception:
        return False


async def _find_button(pil, eye: AIEye, descriptions: List[str]) -> Optional[dict]:
    """Try multiple button descriptions; return first confident match."""
    for desc in descriptions:
        pos = await eye.find_element(pil, desc)
        if pos and pos.get("confidence") in ("high", "medium"):
            return pos
    return None


async def _human_read_page(page: Page, mouse: HumanMouse) -> None:
    """Simulate a human reading the job listing before applying."""
    total_h = await page.evaluate("document.body.scrollHeight")
    vp_h = (page.viewport_size or {}).get("height", 768)
    steps = max(2, total_h // vp_h)

    for step in range(1, steps + 1):
        scroll_y = int((step / steps) * total_h * 0.75)
        await page.evaluate(f"window.scrollTo({{top: {scroll_y}, behavior: 'smooth'}})")
        await asyncio.sleep(random.uniform(1.0, 2.5))

    await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
    await asyncio.sleep(random.uniform(0.5, 1.2))


def _direct_apply_url(url: str) -> str:
    base = url.rstrip("/")
    if "jobs.lever.co" in url and "/apply" not in url:
        return base + "/apply"
    if "jobs.ashbyhq.com" in url and "/apply" not in url:
        return base + "/apply"
    return url


