import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import BrowserContext, async_playwright
from playwright_stealth import Stealth

from agent.brain.human_brain import HumanBrain
from agent.browser.captcha_detector import page_has_captcha, url_is_blocked
from agent.phases.search_planner import SearchPlanner, SearchStrategy

logger = logging.getLogger(__name__)


@dataclass
class RawJob:
    title: str
    company: str
    url: str
    description: str
    platform: str
    location: Optional[str] = None
    posted_at: Optional[datetime] = None


# Selectors tried (in order) when extracting a full job description.
_DESC_SELECTORS = [
    '[class*="job-description"]',
    '[class*="jobDescription"]',
    '[class*="job-detail"]',
    '[class*="jobDetail"]',
    '[data-qa="job-description"]',
    '.posting-description',
    '.section-wrapper',
    '.job-content',
    'article',
    'main',
    '.content',
    '#content',
]


class ReadPhase:
    def __init__(self, user: Any, preferences: Any):
        self.user = user
        self.preferences = preferences
        self.jobs: List[RawJob] = []
        self.brain = HumanBrain(str(user.id))

        # User-specific persistent browser profile
        self.profile_dir = (
            Path(__file__).parent.parent / "browser" / "profiles" / str(user.id)
        )
        os.makedirs(self.profile_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def execute(self) -> List[RawJob]:
        """Discover relevant job postings using strategy + full-page read."""
        planner = SearchPlanner(self.user, self.preferences)
        strategies = await planner.generate_strategies()
        logger.info(
            f"Generated {len(strategies)} search strategies for user {self.user.id}"
        )

        for strategy in strategies:
            try:
                logger.info(
                    f"Executing search — niche: {strategy.niche!r} | "
                    f"query: {strategy.query!r}"
                )
                if "DDG" in strategy.target_platforms:
                    ddg_jobs = await self._search_ddg(strategy.query)
                    self.jobs.extend(ddg_jobs)

                if "Google" in strategy.target_platforms and len(self.jobs) < 5:
                    google_jobs = await self._search_google_jobs(strategy.query)
                    self.jobs.extend(google_jobs)

            except Exception as e:
                logger.error(f"Search source error for {strategy.query!r}: {e}")

        return self._deduplicate(self.jobs)

    # ------------------------------------------------------------------
    # Browser setup
    # ------------------------------------------------------------------

    async def _setup_browser(self, p) -> BrowserContext:
        """Stealth persistent browser context."""
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-position=0,0",
                "--ignore-certificate-errors",
                "--ignore-certificate-errors-spki-list",
                "--disable-dev-shm-usage",
            ],
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
            has_touch=False,
            is_mobile=False,
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins',   {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
            Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            const _getParam = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(p) {
                if (p === 37445) return 'Intel Open Source Technology Center';
                if (p === 37446) return 'Mesa DRI Intel(R) HD Graphics 5500 (Broadwell GT2)';
                return _getParam.apply(this, arguments);
            };
        """)
        return context

    # ------------------------------------------------------------------
    # DuckDuckGo search
    # ------------------------------------------------------------------

    async def _search_ddg(self, query: str) -> List[RawJob]:
        """
        1. Search DDG for job URLs.
        2. Visit each URL inside the same context to fetch the full description.
        """
        logger.info(f"DDG search: {query!r}")
        full_query = (
            f"{query} "
            "(site:lever.co OR site:ashbyhq.com OR "
            "site:boards.greenhouse.io OR site:workable.com)"
        )
        all_jobs: List[RawJob] = []

        async with async_playwright() as p:
            context = await self._setup_browser(p)
            search_page = await context.new_page()
            await Stealth().apply_stealth_async(search_page)

            try:
                # ---- Step 1: Collect raw result stubs from DDG ----
                raw_results = await self._collect_ddg_results(
                    search_page, full_query
                )
                logger.info(f"DDG collected {len(raw_results)} raw results.")

                # ---- CAPTCHA wall check on the DDG results page ----
                if await page_has_captcha(search_page):
                    logger.warning(
                        "DDG returned a CAPTCHA/bot-wall — skipping this query."
                    )
                    return []

                # ---- Step 2: Visit each URL for the full description ----
                for item in raw_results[:8]:
                    try:
                        if await url_is_blocked(item["url"]):
                            logger.info(
                                f"Skipping blocked portal URL: {item['url']}"
                            )
                            continue

                        full_desc = await self._fetch_full_job_description(
                            context, item["url"]
                        )
                        description = (
                            full_desc
                            if len(full_desc) > 200
                            else item.get("snippet", f"Listing: {item['title']}")
                        )
                        all_jobs.append(
                            RawJob(
                                title=item["title"],
                                company=item["company"],
                                url=item["url"],
                                description=description,
                                platform="Direct Board (DDG)",
                                location="Remote",
                            )
                        )
                        await self.brain.random_sleep(1.0, 2.5)
                    except Exception as e:
                        logger.debug(
                            f"Skipped result {item.get('url', '?')}: {e}"
                        )

            except Exception as e:
                logger.error(f"DDG search failed: {e}")
            finally:
                await context.close()

        return all_jobs

    async def _collect_ddg_results(
        self, page, full_query: str
    ) -> List[Dict[str, str]]:
        """Navigate DDG and return a list of {title, company, url, snippet}."""
        results: List[Dict[str, str]] = []
        try:
            encoded = full_query.replace(" ", "+")
            await page.goto(f"https://duckduckgo.com/?q={encoded}")
            await self.brain.random_sleep(2, 4)

            items = await page.query_selector_all(
                "article, [data-testid='result']"
            )
            for res in items[:12]:
                try:
                    title_el = await res.query_selector(
                        "h2 a, a[data-testid='result-title-a']"
                    )
                    if not title_el:
                        continue

                    url = (await title_el.get_attribute("href") or "").strip()
                    title = (await title_el.inner_text() or "").strip()

                    if not url or not url.startswith("http"):
                        continue

                    snippet_el = await res.query_selector(
                        "div > span, [data-testid='result-snippet']"
                    )
                    snippet = (
                        (await snippet_el.inner_text()).strip()
                        if snippet_el
                        else ""
                    )

                    company = _company_from_url(url)

                    results.append(
                        {
                            "title": title,
                            "company": company,
                            "url": url,
                            "snippet": snippet,
                        }
                    )
                except Exception as e:
                    logger.debug(f"DDG row parse skipped: {e}")

        except Exception as e:
            logger.error(f"DDG results page error: {e}")

        return results

    # ------------------------------------------------------------------
    # Google Jobs fallback
    # ------------------------------------------------------------------

    async def _search_google_jobs(self, query: str) -> List[RawJob]:
        """Google Jobs fallback — visits listing pages for full descriptions."""
        all_jobs: List[RawJob] = []
        async with async_playwright() as p:
            context = await self._setup_browser(p)
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)

            try:
                search_url = (
                    f"https://www.google.com/search?"
                    f"q={query.replace(' ', '+')}+jobs&ibp=htl;jobs"
                )
                logger.info(f"Google Jobs fallback: {search_url}")
                await page.goto(search_url)
                await self.brain.random_sleep(3, 6)
                await self.brain.handle_interruptions(page)

                if "unusual traffic" in (await page.content()).lower():
                    logger.warning("Google blocked request (bot detection).")
                    return []

                await self.brain.read_page(page)

                job_items = (await page.query_selector_all("li"))[:7]
                for i, item in enumerate(job_items):
                    try:
                        title_el = await item.query_selector(
                            "div[role='heading']"
                        )
                        company_el = await item.query_selector(
                            "div > div > div > div:nth-child(1)"
                        )
                        if not (title_el and company_el):
                            continue

                        title = (await title_el.inner_text()).strip()
                        company = (await company_el.inner_text()).strip()

                        await self.brain.click_element(
                            page, f"li:nth-child({i + 1})"
                        )
                        await self.brain.random_sleep(2, 4)

                        desc_el = await page.query_selector(
                            "[data-full-description='true']"
                        )
                        description = (
                            (await desc_el.inner_text()).strip()
                            if desc_el
                            else "No description"
                        )

                        apply_btns = await page.query_selector_all(
                            "a:has-text('Apply')"
                        )
                        url = ""
                        for btn in apply_btns:
                            href = await btn.get_attribute("href")
                            if href and "google.com" not in href:
                                url = href
                                break

                        if url and not await url_is_blocked(url):
                            # Fetch fuller description from the direct URL
                            full_desc = await self._fetch_full_job_description(
                                context, url
                            )
                            if len(full_desc) > 200:
                                description = full_desc

                            all_jobs.append(
                                RawJob(
                                    title=title,
                                    company=company,
                                    url=url,
                                    description=description,
                                    platform="Google Jobs",
                                    location="Remote",
                                )
                            )
                    except Exception:
                        continue

            except Exception as e:
                logger.error(f"Google Jobs search failed: {e}")
            finally:
                await context.close()

        return all_jobs

    # ------------------------------------------------------------------
    # Full job description extractor
    # ------------------------------------------------------------------

    async def _fetch_full_job_description(
        self, context: BrowserContext, url: str
    ) -> str:
        """
        Open *url* in a new tab, scroll through it (human-like), and
        extract the longest coherent block of job description text found
        using a prioritised list of CSS selectors.
        """
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.brain.random_sleep(1.5, 3.0)
            await self.brain.handle_interruptions(page)

            if await page_has_captcha(page):
                logger.warning(f"CAPTCHA wall detected on job page — skipping: {url}")
                return ""

            selectors_js = json.dumps(_DESC_SELECTORS)
            text: str = await page.evaluate(
                f"""
                () => {{
                    const selectors = {selectors_js};
                    for (const sel of selectors) {{
                        const el = document.querySelector(sel);
                        if (el && el.innerText.trim().length > 200) {{
                            return el.innerText.trim().substring(0, 5000);
                        }}
                    }}
                    // Last resort: whole body
                    return document.body.innerText.trim().substring(0, 5000);
                }}
                """
            )
            return text or ""
        except Exception as e:
            logger.debug(f"Could not fetch full description from {url}: {e}")
            return ""
        finally:
            await page.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _deduplicate(self, jobs: List[RawJob]) -> List[RawJob]:
        seen_urls: set = set()
        unique: List[RawJob] = []
        for job in jobs:
            if job.url not in seen_urls:
                unique.append(job)
                seen_urls.add(job.url)
        return unique


# ------------------------------------------------------------------
# Module-level helper
# ------------------------------------------------------------------

def _company_from_url(url: str) -> str:
    """Extract a company slug from well-known ATS URL patterns."""
    patterns = [
        ("lever.co/", 1),
        ("greenhouse.io/", 1),
        ("ashbyhq.com/", 1),
        ("workable.com/", 1),
    ]
    for pattern, segment_index in patterns:
        if pattern in url:
            try:
                return url.split(pattern)[1].split("/")[segment_index - 1]
            except IndexError:
                pass
    return "Unknown"
