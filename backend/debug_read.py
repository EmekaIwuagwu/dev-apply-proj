import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from agent.brain.human_brain import HumanBrain
import os

async def debug_google_jobs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=1,
            locale="en-NG",
            timezone_id="Africa/Lagos"
        )
        # Mask webdriver
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        brain = HumanBrain("debug_user_123")
        query = "Python React Fullstack jobs"
        
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&ibp=htl;jobs"
        print(f"Navigating to {search_url}...")
        
        await page.goto(search_url)
        await brain.random_sleep(2, 4)
        
        # Take a screenshot
        screenshot_path = os.path.join(os.getcwd(), "google_jobs_direct_debug.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to: {screenshot_path}")
        
        # Check results
        title = await page.title()
        print(f"Page title: {title}")
        
        content = await page.content()
        if "unusual traffic" in content.lower() or await page.query_selector("iframe[src*='recaptcha']") or await page.query_selector("iframe[src*='consent']"):
            print("RECAPTCHA or CONSENT DETECTED")
        else:
            print("NO RECAPTCHA")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_google_jobs())
