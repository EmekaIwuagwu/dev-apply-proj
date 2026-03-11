"""
Job discovery via DuckDuckGo.
Targets Lever and Ashby ATS portals exclusively — both are CAPTCHA-free
and support direct browser automation.
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from playwright.async_api import BrowserContext, async_playwright
from playwright_stealth import Stealth

from agent.llm import LLMClient

logger = logging.getLogger(__name__)

_DDG_SEARCH = "https://duckduckgo.com/?q={query}"

# Only these two ATS portals — no CAPTCHA, no account wall
_ATS_FILTER = "(site:jobs.lever.co OR site:jobs.ashbyhq.com)"

# Portals that are explicitly off-limits
_BLOCKED_DOMAINS = [
    "greenhouse.io",
    "workable.com",
    "myworkdayjobs.com",
    "linkedin.com",
    "indeed.com",
]


@dataclass
class DiscoveredJob:
    title: str
    company: str
    url: str
    description: str
    platform: str


async def discover_jobs(
    user,
    preferences,
    profile_dir: str,
) -> List[DiscoveredJob]:
    """
    Build search queries from the user's job titles + skills, search DDG,
    visit each result page to extract the full description, and return
    a de-duplicated list of DiscoveredJob objects.
    """
    queries = _build_queries(preferences)
    if not queries:
        logger.warning(f"User {user.id} has no job titles — nothing to search")
        return []

    logger.info(f"User {user.id}: {len(queries)} search queries")
    jobs: List[DiscoveredJob] = []

    async with async_playwright() as p:
        context = await _make_context(p, profile_dir)
        try:
            for query in queries:
                try:
                    found = await _run_query(context, query)
                    jobs.extend(found)
                    if len(jobs) >= 20:
                        break
                    await asyncio.sleep(3)
                except Exception as e:
                    logger.error(f"Query {query!r} failed: {e}")
        finally:
            await context.close()

    return _dedupe(jobs)


# ---------------------------------------------------------------------------
# Query builder
# ---------------------------------------------------------------------------

def _build_queries(preferences) -> List[str]:
    titles: List[str] = list(getattr(preferences, "job_titles", []) or [])
    skills: List[str] = list(getattr(preferences, "skills", []) or [])
    top_skills = " ".join(skills[:4])

    queries = []
    for title in titles[:4]:
        q = f'"{title}"'
        if top_skills:
            q += f" {top_skills}"
        q += f" {_ATS_FILTER}"
        queries.append(q)

    return queries


# ---------------------------------------------------------------------------
# DDG search
# ---------------------------------------------------------------------------

async def _run_query(context: BrowserContext, query: str) -> List[DiscoveredJob]:
    page = await context.new_page()
    await Stealth().apply_stealth_async(page)
    jobs: List[DiscoveredJob] = []

    try:
        encoded = query.replace(" ", "+")
        await page.goto(_DDG_SEARCH.format(query=encoded), wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)

        # Check for CAPTCHA / bot wall
        body = (await page.content()).lower()
        if any(s in body for s in ("captcha", "robot", "unusual traffic", "verify")):
            logger.warning("DDG bot-wall detected — skipping query")
            return []

        # Collect result links
        links = await page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll('article a[href], [data-testid="result"] a[href]').forEach(a => {
                    const href = a.href || '';
                    const text = a.innerText?.trim() || '';
                    if (href.startsWith('http') && text) {
                        results.push({url: href, title: text});
                    }
                });
                return results;
            }
        """)

        # Filter to ATS portals only
        ats_links = [
            r for r in links
            if "jobs.lever.co" in r["url"] or "jobs.ashbyhq.com" in r["url"]
        ][:8]

        logger.info(f"DDG: {len(ats_links)} ATS results for {query!r}")

        for item in ats_links:
            url = item["url"]
            if _is_blocked(url):
                continue
            # Skip /apply URLs from search — we want the listing page
            if url.endswith("/apply") or "/apply?" in url:
                url = url.rsplit("/apply", 1)[0]

            try:
                desc, company = await _fetch_job_page(context, url)
                if not desc:
                    continue
                jobs.append(DiscoveredJob(
                    title=item["title"],
                    company=company or _company_from_url(url),
                    url=url,
                    description=desc,
                    platform="Lever" if "lever.co" in url else "Ashby",
                ))
                await asyncio.sleep(1)
            except Exception as e:
                logger.debug(f"Skipped {url}: {e}")

    except Exception as e:
        logger.error(f"DDG page error: {e}")
    finally:
        await page.close()

    return jobs


async def _fetch_job_page(context: BrowserContext, url: str) -> tuple[str, str]:
    """
    Open the job listing page and extract:
      - the job description text
      - the company name (from the page or URL)
    """
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(1)

        # Check for bot wall / CAPTCHA on this page
        body_lower = (await page.content()).lower()
        if any(s in body_lower for s in ("captcha", "challenge", "verify you are human")):
            return "", ""

        result = await page.evaluate("""
            () => {
                // Description selectors ordered by specificity
                const descSelectors = [
                    '.posting-description', '[class*="job-description"]',
                    '[class*="jobDescription"]', '[class*="job-detail"]',
                    '[data-qa="job-description"]', '.section-wrapper',
                    '.job-content', 'article', 'main'
                ];
                let desc = '';
                for (const sel of descSelectors) {
                    const el = document.querySelector(sel);
                    if (el && el.innerText.trim().length > 200) {
                        desc = el.innerText.trim().substring(0, 4000);
                        break;
                    }
                }
                if (!desc) {
                    desc = document.body.innerText.trim().substring(0, 4000);
                }

                // Company name
                let company = '';
                const og = document.querySelector('meta[property="og:site_name"]');
                if (og) company = og.content;
                if (!company) {
                    const title = document.title || '';
                    const parts = title.split(/[|\\-–—at]/i);
                    if (parts.length > 1) company = parts[parts.length - 1].trim();
                }

                return {desc, company};
            }
        """)
        return result.get("desc", ""), result.get("company", "")
    except Exception as e:
        logger.debug(f"Fetch failed {url}: {e}")
        return "", ""
    finally:
        await page.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_context(p, profile_dir: str) -> BrowserContext:
    import os
    os.makedirs(profile_dir, exist_ok=True)
    ctx = await p.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
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


def _is_blocked(url: str) -> bool:
    return any(d in url for d in _BLOCKED_DOMAINS)


def _company_from_url(url: str) -> str:
    for prefix in ("jobs.lever.co/", "jobs.ashbyhq.com/"):
        if prefix in url:
            try:
                return url.split(prefix)[1].split("/")[0]
            except IndexError:
                pass
    return "Unknown"


def _dedupe(jobs: List[DiscoveredJob]) -> List[DiscoveredJob]:
    seen, unique = set(), []
    for j in jobs:
        if j.url not in seen:
            unique.append(j)
            seen.add(j.url)
    return unique
