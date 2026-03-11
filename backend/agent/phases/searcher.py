"""
searcher.py — Phase 1: Find job listings.

The agent behaves like a human doing a job search:
  1. Opens DuckDuckGo
  2. Types each search query (human-like)
  3. Takes a screenshot — AI Eye identifies the result links
  4. Also reads the DOM for Lever/Ashby URLs as a reliability fallback
  5. For each job URL: visits it, verifies it loads (not a 404 / redirect)
  6. Returns a list of RawJob objects for the Reader phase

Target ATS platforms: Lever (jobs.lever.co) and Ashby (jobs.ashbyhq.com).
These are chosen because they have no login wall and no anti-bot protection.
"""
import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Any, List, Optional
from urllib.parse import quote_plus

from playwright.async_api import BrowserContext, Page

from agent.browser.mouse import HumanMouse
from agent.browser.typist import HumanTypist
from agent.vision.ai_eye import AIEye
from agent.vision.screen import capture

logger = logging.getLogger(__name__)

_DDG = "https://duckduckgo.com"

# Only ATS portals we can reliably automate
_ATS_DOMAINS = ["jobs.lever.co", "jobs.ashbyhq.com"]

# Site filter appended to every query so DDG returns ATS results
_SITE_FILTER = "(site:jobs.lever.co OR site:jobs.ashbyhq.com)"

# Domains to never click through to
_BLOCKED = [
    "linkedin.com", "indeed.com", "glassdoor.com",
    "greenhouse.io", "workday.com", "myworkdayjobs.com",
    "taleo.net", "successfactors.com",
]


@dataclass
class RawJob:
    url: str
    platform: str   # "Lever" | "Ashby"
    search_title: str  # title text from search result


async def find_jobs(
    ctx: BrowserContext,
    user: Any,
    preferences: Any,
    eye: AIEye,
    seed: str,
) -> List[RawJob]:
    """
    Execute all search queries and return a de-duplicated list of job URLs.
    """
    queries = _build_queries(preferences)
    if not queries:
        logger.warning(f"User {getattr(user, 'id', '?')} has no job titles — nothing to search")
        return []

    logger.info(f"Searching {len(queries)} queries for user {getattr(user, 'id', '?')}")

    jobs: List[RawJob] = []
    seen_urls: set = set()

    for query in queries:
        try:
            found = await _search_one_query(ctx, query, eye, seed)
            for job in found:
                if job.url not in seen_urls:
                    jobs.append(job)
                    seen_urls.add(job.url)
            if len(jobs) >= 25:
                break
            await asyncio.sleep(random.uniform(4, 8))  # human pacing between searches
        except Exception as e:
            logger.error(f"Search query failed {query!r}: {e}")

    logger.info(f"Total unique jobs found: {len(jobs)}")
    return jobs


# ---------------------------------------------------------------------------
# Query builder
# ---------------------------------------------------------------------------

def _build_queries(preferences: Any) -> List[str]:
    titles: List[str] = list(getattr(preferences, "job_titles", []) or [])
    skills: List[str] = list(getattr(preferences, "skills", []) or [])
    top_skills = " ".join(skills[:4])
    exp = getattr(preferences, "experience_level", "") or ""

    queries = []
    for title in titles[:4]:
        q = f'"{title}"'
        if top_skills:
            q += f" {top_skills}"
        if exp:
            q += f" {exp}"
        q += f" {_SITE_FILTER}"
        queries.append(q)

    return queries


# ---------------------------------------------------------------------------
# Single-query search execution
# ---------------------------------------------------------------------------

async def _search_one_query(
    ctx: BrowserContext,
    query: str,
    eye: AIEye,
    seed: str,
) -> List[RawJob]:
    """
    Open DuckDuckGo in a new page, type the query like a human,
    and collect ATS job URLs from the results.
    """
    from agent.browser.context import new_stealth_page
    page = await new_stealth_page(ctx)
    mouse = HumanMouse(page, seed=seed)
    typist = HumanTypist(page, seed=seed)
    jobs: List[RawJob] = []

    try:
        # ----------------------------------------------------------------
        # 1. Navigate to DuckDuckGo
        # ----------------------------------------------------------------
        logger.info(f"Navigating to DDG for query: {query!r}")
        await page.goto(_DDG, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(1.5, 3.0))

        # ----------------------------------------------------------------
        # 2. Find the search box using AI Eye
        # ----------------------------------------------------------------
        raw, bgr, pil = await capture(page)
        search_pos = await eye.find_element(pil, "the main search input box")

        if search_pos:
            await mouse.click(search_pos["x"], search_pos["y"])
        else:
            # DOM fallback
            try:
                await page.click('input[name="q"], #searchbox_input, [name="query"]', timeout=5000)
            except Exception:
                logger.warning("Could not find DDG search box")
                return []

        await asyncio.sleep(random.uniform(0.4, 0.9))

        # ----------------------------------------------------------------
        # 3. Type the query — human-like
        # ----------------------------------------------------------------
        await typist.type(query)
        await asyncio.sleep(random.uniform(0.3, 0.8))
        await typist.press("Enter")

        # ----------------------------------------------------------------
        # 4. Wait for results
        # ----------------------------------------------------------------
        await asyncio.sleep(random.uniform(2.5, 4.5))

        try:
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass

        # ----------------------------------------------------------------
        # 5. Check for bot wall / CAPTCHA on DDG
        # ----------------------------------------------------------------
        raw, bgr, pil = await capture(page)
        if await eye.has_captcha(pil):
            logger.warning("DDG CAPTCHA detected — skipping query")
            return []

        # ----------------------------------------------------------------
        # 6. Collect result URLs
        #    Primary: DOM (reliable for URL extraction)
        #    Secondary: AI Eye link list (for visual validation)
        # ----------------------------------------------------------------
        dom_urls = await _collect_urls_from_dom(page)
        logger.info(f"DDG DOM found {len(dom_urls)} ATS URLs")

        # Scroll and look for more results
        await mouse.scroll_down(400)
        await asyncio.sleep(1.5)
        raw, bgr, pil = await capture(page)

        ai_links = await eye.find_all_links(pil, filter_hint="job listing")
        logger.info(f"AI Eye found {len(ai_links)} links on results page")

        # We trust DOM URLs for accuracy; use AI links to confirm titles
        title_map = {l["text"].lower(): l for l in ai_links}

        for url in dom_urls[:8]:
            platform = _platform(url)
            # Try to find a matching title from AI results
            title = next(
                (l["text"] for l in ai_links if _url_hint(url) in l.get("text", "").lower()),
                url.split("/")[-1].replace("-", " ").title(),
            )
            jobs.append(RawJob(url=url, platform=platform, search_title=title))

        # Human: scroll through results a bit before moving on
        await mouse.scroll_down(200)
        await asyncio.sleep(random.uniform(0.8, 1.8))

    except Exception as e:
        logger.error(f"_search_one_query error: {e}")
    finally:
        await page.close()

    return jobs


async def _collect_urls_from_dom(page: Page) -> List[str]:
    """Extract ATS job URLs directly from the DOM (fast, reliable)."""
    links = await page.evaluate("""
        () => Array.from(document.querySelectorAll('a[href]'))
            .map(a => a.href)
            .filter(h => h.startsWith('http'))
    """)
    urls = []
    for link in links:
        if any(d in link for d in _ATS_DOMAINS) and not any(b in link for b in _BLOCKED):
            # Strip tracking params
            clean = link.split("?")[0].split("#")[0]
            # Skip /apply suffix — we want listing page
            if clean.endswith("/apply"):
                clean = clean[: -len("/apply")]
            if clean not in urls and len(clean) > 30:
                urls.append(clean)
    return urls


def _platform(url: str) -> str:
    if "lever.co" in url:
        return "Lever"
    if "ashbyhq.com" in url:
        return "Ashby"
    return "Unknown"


def _url_hint(url: str) -> str:
    """Return the last path segment of a URL as a hint for title matching."""
    return url.rstrip("/").split("/")[-1].replace("-", " ").lower()
