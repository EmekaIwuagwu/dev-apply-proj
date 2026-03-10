import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def test_ddg():
    # Simulate agent persistent context
    profile_dir = Path(__file__).parent / "test_profile"
    os.makedirs(profile_dir, exist_ok=True)
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        # Mask fingerprint indicators
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
            Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
        """)
        
        query = "Python Developer jobs site:lever.co"
        print(f"Searching for: {query} on BING")
        await page.goto(f"https://www.bing.com/search?q={query.replace(' ', '+')}", wait_until="networkidle")
        await asyncio.sleep(5)
        
        await page.screenshot(path="ddg_stealth_test.png")
        print("Screenshot saved to ddg_stealth_test.png")
        
        results = await page.query_selector_all("article, [data-testid='result']")
        print(f"Found {len(results)} results")
        
        await context.close()

if __name__ == "__main__":
    asyncio.run(test_ddg())
