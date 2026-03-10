import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from agent.brain.human_brain import HumanBrain
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

import os
from pathlib import Path

class ReadPhase:
    def __init__(self, user: Any, preferences: Any):
        self.user = user
        self.preferences = preferences
        self.jobs: List[RawJob] = []
        self.brain = HumanBrain(str(user.id))
        
        # User-specific browser profile directory
        self.profile_dir = Path(__file__).parent.parent / "browser" / "profiles" / str(user.id)
        os.makedirs(self.profile_dir, exist_ok=True)

    async def execute(self) -> List[RawJob]:
        """
        Discover relevant job postings based on user-specific search strategy.
        """
        # 0. Planning Phase: Generate Niche Strategies
        planner = SearchPlanner(self.user, self.preferences)
        strategies = await planner.generate_strategies()
        logger.info(f"Generated {len(strategies)} high-impact search strategies for user {self.user.id}")
        
        # Sequential search to avoid multi-browser detection and resource spikes
        for strategy in strategies:
            try:
                logger.info(f"Executing search for niche: {strategy.niche} ({strategy.query})...")
                # 1. Primary: DuckDuckGo (targets direct boards, less bot-repellant)
                if "DDG" in strategy.target_platforms:
                    ddg_jobs = await self._search_ddg(strategy.query)
                    self.jobs.extend(ddg_jobs)
                
                # 2. Fallback: Google Jobs (if DDG yields little or preferred)
                if "Google" in strategy.target_platforms and len(self.jobs) < 5:
                    google_jobs = await self._search_google_jobs(strategy.query)
                    self.jobs.extend(google_jobs)
                    
            except Exception as e:
                logger.error(f"Search source error for '{strategy.query}': {e}")

        return self._deduplicate(self.jobs)

    # Defunct method — replaced by SearchPlanner
    # def _build_search_queries(self) -> List[str]: ...

    async def _setup_browser(self, p):
        """Standardized stealth browser setup with persistent context."""
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-position=0,0",
                "--ignore-certifcate-errors",
                "--ignore-certifcate-errors-spki-list",
                "--disable-dev-shm-usage"
            ],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=1,
            has_touch=False,
            is_mobile=False,
        )
        
        # Enhanced Fingerprint Masking
        await context.add_init_script("""
            // Mask WebDriver
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            
            // Mask Plugins
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            
            // Mask Hardware
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
            Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            
            // WebGL Spoofing
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Open Source Technology Center';
                if (parameter === 37446) return 'Mesa DRI Intel(R) HD Graphics 5500 (Broadwell GT2)';
                return getParameter.apply(this, arguments);
            };
        """)
        
        return context

    async def _search_ddg(self, query: str) -> List[RawJob]:
        """Search DuckDuckGo with site-specific operators to find direct application pages."""
        logger.info(f"Targeting direct boards via DuckDuckGo: {query}")
        all_jobs = []
        
        # Use broader query (remove restrictive quotes)
        full_query = f'{query} (site:lever.co OR site:ashbyhq.com OR site:boards.greenhouse.io OR site:workable.com)'
        logger.info(f"Searching DDG with query: {full_query}")
        
        async with async_playwright() as p:
            context = await self._setup_browser(p)
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            
            try:
                await page.goto(f"https://duckduckgo.com/?q={full_query.replace(' ', '+')}")
                await self.brain.random_sleep(2, 4)
                
                # Updated selectors based on live DOM check
                results = await page.query_selector_all("article, [data-testid='result']")
                logger.info(f"DDG found {len(results)} raw result containers.")
                
                for res in results[:10]:
                    try:
                        # Try multiple title/link patterns
                        title_el = await res.query_selector("h2 a, a[data-testid='result-title-a']")
                        if not title_el: continue
                        
                        url = await title_el.get_attribute("href")
                        title = await title_el.inner_text()
                        
                        # Description/Snippet
                        snippet_el = await res.query_selector("div > span, [data-testid='result-snippet']")
                        description = await snippet_el.inner_text() if snippet_el else f"Listing: {title}"
                        
                        # Company extraction from URL or Breadcrumb
                        company = "Unknown"
                        breadcrumb = await res.query_selector("article a.Rn_JXVtoPVAFyGkcaXyK, [data-testid='result-extras-url-link']")
                        breadcrumb_text = await breadcrumb.inner_text() if breadcrumb else ""
                        
                        if "lever.co/" in url: company = url.split("lever.co/")[1].split("/")[0]
                        elif "greenhouse.io/" in url: company = url.split("greenhouse.io/")[1].split("/")[0]
                        elif breadcrumb_text and " › " in breadcrumb_text:
                            # e.g. jobs.lever.co › TalentNeuron
                            parts = breadcrumb_text.split(" › ")
                            if len(parts) > 1: company = parts[1].strip()

                        all_jobs.append(RawJob(
                            title=title,
                            company=company,
                            url=url,
                            description=description,
                            platform="Direct Board (DDG)",
                            location="Remote"
                        ))
                    except Exception as e:
                        logger.debug(f"Row extraction skipped: {e}")
                        continue
                    
            except Exception as e:
                logger.error(f"DDG Search failed: {e}")
            finally:
                await context.close()
        
        return all_jobs

    async def _search_google_jobs(self, query: str) -> List[RawJob]:
        """Searches Google Jobs portal with maximum evasion."""
        all_jobs = []
        async with async_playwright() as p:
            context = await self._setup_browser(p)
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            
            try:
                search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}+jobs&ibp=htl;jobs"
                logger.info(f"Google Jobs Fallback: {search_url}")
                await page.goto(search_url)
                
                await self.brain.random_sleep(3, 6)
                await self.brain.handle_interruptions(page)
                
                if "unusual traffic" in (await page.content()).lower():
                    logger.warning("Google blocked request (Detection).")
                    return []

                await self.brain.read_page(page)
                
                job_items = (await page.query_selector_all("li"))[:7]
                for i, item in enumerate(job_items):
                    try:
                        title_el = await item.query_selector("div[role='heading']")
                        company_el = await item.query_selector("div > div > div > div:nth-child(1)")
                        
                        if title_el and company_el:
                            title = await title_el.inner_text()
                            company = await company_el.inner_text()
                            
                            await self.brain.click_element(page, f"li:nth-child({i+1})")
                            await self.brain.random_sleep(2, 4)
                            
                            desc_el = await page.query_selector("[data-full-description='true']")
                            description = await desc_el.inner_text() if desc_el else "No description"
                            
                            apply_btns = await page.query_selector_all("a:has-text('Apply')")
                            url = ""
                            for btn in apply_btns:
                                href = await btn.get_attribute("href")
                                if href and "google.com" not in href:
                                    url = href
                                    break
                            
                            if url:
                                all_jobs.append(RawJob(
                                    title=title, company=company, url=url,
                                    description=description, platform="Google Jobs", location="Remote"
                                ))
                    except: continue
            except Exception as e:
                logger.error(f"Google search failed: {e}")
            finally:
                await context.close()
        return all_jobs

    def _deduplicate(self, jobs: List[RawJob]) -> List[RawJob]:
        seen_urls = set()
        unique_jobs = []
        for job in jobs:
            if job.url not in seen_urls:
                unique_jobs.append(job)
                seen_urls.add(job.url)
        return unique_jobs
