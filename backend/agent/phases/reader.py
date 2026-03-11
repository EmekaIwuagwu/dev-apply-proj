"""
reader.py — Phase 2: Read each job page and decide whether to apply.

The agent behaves like a human evaluating a job posting:
  1. Opens the job listing page
  2. Scrolls through it naturally (reading speed)
  3. Takes a screenshot
  4. AI Eye reads all the visible text (vision-first — sees what a human sees)
  5. LLM evaluates: does this match the candidate? score 0–100
  6. If score >= 70 → schedule for application
  7. Returns a list of EvaluatedJob objects
"""
import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Any, List, Optional

from playwright.async_api import BrowserContext

from agent.browser.context import new_stealth_page
from agent.browser.mouse import HumanMouse
from agent.phases.searcher import RawJob
from agent.vision.ai_eye import AIEye
from agent.vision.screen import capture

logger = logging.getLogger(__name__)

_APPLY_THRESHOLD = 70  # Score 0–100; jobs below this are skipped


@dataclass
class EvaluatedJob:
    url: str
    platform: str
    title: str
    company: str
    score: int
    reasoning: str
    cover_note: str
    description: str     # raw extracted text (for DB storage)


def _build_profile_text(user: Any, preferences: Any) -> str:
    skills = list(getattr(preferences, "skills", []) or []) if preferences else []
    exp = (getattr(preferences, "experience_level", "") or "") if preferences else ""
    titles = list(getattr(preferences, "job_titles", []) or []) if preferences else []
    locs = list(getattr(preferences, "preferred_locations", []) or []) if preferences else []
    excl = list(getattr(preferences, "excluded_companies", []) or []) if preferences else []
    salary_min = getattr(preferences, "salary_min", None) if preferences else None
    salary_max = getattr(preferences, "salary_max", None) if preferences else None

    salary_str = ""
    if salary_min or salary_max:
        salary_str = f"  Salary range   : {salary_min or '?'}–{salary_max or '?'}\n"

    return (
        f"  Name           : {getattr(user, 'full_name', '')}\n"
        f"  Bio            : {getattr(user, 'bio', '')[:400]}\n"
        f"  Skills         : {', '.join(skills)}\n"
        f"  Experience     : {exp}\n"
        f"  Target titles  : {', '.join(titles)}\n"
        f"  Locations      : {', '.join(locs) or 'open to remote'}\n"
        f"  Excluded cos   : {', '.join(excl)}\n"
        f"{salary_str}"
    )


async def evaluate_jobs(
    ctx: BrowserContext,
    raw_jobs: List[RawJob],
    user: Any,
    preferences: Any,
    eye: AIEye,
    seed: str,
) -> List[EvaluatedJob]:
    """
    Visit every raw job URL, read the page, score it.
    Returns only jobs that pass the threshold.
    """
    profile_text = _build_profile_text(user, preferences)
    evaluated: List[EvaluatedJob] = []

    for job in raw_jobs:
        try:
            result = await _evaluate_one(ctx, job, profile_text, eye, seed)
            if result:
                evaluated.append(result)
                logger.info(
                    f"ACCEPTED [{result.score}] {result.title} @ {result.company}"
                )
            # Human pacing between job reads
            await asyncio.sleep(random.uniform(3, 7))
        except Exception as e:
            logger.error(f"Error evaluating {job.url}: {e}")

    logger.info(f"Reader phase: {len(evaluated)}/{len(raw_jobs)} jobs accepted")
    return evaluated


async def _evaluate_one(
    ctx: BrowserContext,
    job: RawJob,
    profile_text: str,
    eye: AIEye,
    seed: str,
) -> Optional[EvaluatedJob]:
    page = await new_stealth_page(ctx)
    mouse = HumanMouse(page, seed=seed)

    try:
        # ----------------------------------------------------------------
        # 1. Load the job page
        # ----------------------------------------------------------------
        logger.info(f"Reading: {job.url}")
        await page.goto(job.url, wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(random.uniform(1.5, 3.0))

        # Dismiss cookie banners
        await _dismiss_banners(page)

        # ----------------------------------------------------------------
        # 2. Human reading: scroll through the page naturally
        # ----------------------------------------------------------------
        total_h = await page.evaluate("document.body.scrollHeight")
        vp_h = (page.viewport_size or {}).get("height", 768)
        scroll_steps = max(2, total_h // vp_h)

        for step in range(1, scroll_steps + 1):
            scroll_y = int((step / scroll_steps) * total_h * 0.8)
            await page.evaluate(f"window.scrollTo({{top: {scroll_y}, behavior: 'smooth'}})")
            # Reading pause — proportional to page length
            read_time = random.uniform(0.8, 2.0) if step < scroll_steps else random.uniform(1.5, 3.0)
            await asyncio.sleep(read_time)

        # Scroll back to top before taking the "decision screenshot"
        await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        await asyncio.sleep(1.0)

        # ----------------------------------------------------------------
        # 3. Capture screenshot and check for CAPTCHA
        # ----------------------------------------------------------------
        raw, bgr, pil = await capture(page)

        if await eye.has_captcha(pil):
            logger.warning(f"CAPTCHA on job page — skipping: {job.url}")
            return None

        # ----------------------------------------------------------------
        # 4. AI Eye reads the page content (vision-first)
        # ----------------------------------------------------------------
        page_text = await eye.read_page_content(pil)

        if not page_text or len(page_text) < 100:
            # Fallback: extract text from DOM
            page_text = await page.evaluate(
                "document.body.innerText.trim().substring(0, 5000)"
            )

        # ----------------------------------------------------------------
        # 5. AI decision: should we apply?
        # ----------------------------------------------------------------
        decision = await eye.should_apply(pil, profile_text, page_text)

        if not decision.get("apply"):
            reason = decision.get("skip_reason", "score below threshold")
            logger.debug(f"SKIPPED: {job.url} — {reason}")
            return None

        score = int(decision.get("score", 0))
        if score < _APPLY_THRESHOLD:
            logger.debug(f"SKIPPED [{score}]: {job.url}")
            return None

        return EvaluatedJob(
            url=job.url,
            platform=job.platform,
            title=decision.get("title") or job.search_title,
            company=decision.get("company") or _company_from_url(job.url),
            score=score,
            reasoning=decision.get("reasoning", ""),
            cover_note=decision.get("cover_note", ""),
            description=page_text[:3000],
        )

    except Exception as e:
        logger.error(f"_evaluate_one failed {job.url}: {e}")
        return None
    finally:
        await page.close()


async def _dismiss_banners(page) -> None:
    """Dismiss cookie consent / GDPR banners if present."""
    for sel in [
        "button:has-text('Accept all')",
        "button:has-text('Accept cookies')",
        "button:has-text('I agree')",
        "button:has-text('Agree')",
        "button:has-text('Got it')",
        "button:has-text('OK')",
        "[id*='cookie'] button",
        "[class*='cookie'] button",
    ]:
        try:
            btn = await page.wait_for_selector(sel, timeout=1000, state="visible")
            if btn:
                await btn.click()
                await asyncio.sleep(0.8)
                return
        except Exception:
            pass


def _company_from_url(url: str) -> str:
    for prefix in ("jobs.lever.co/", "jobs.ashbyhq.com/"):
        if prefix in url:
            try:
                return url.split(prefix)[1].split("/")[0].replace("-", " ").title()
            except IndexError:
                pass
    return "Unknown"
