import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def debug_page():
    url = "https://jobs.lever.co/provectus/cbd7d5f6-b565-4225-854a-08c5b9a66097"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await Stealth().apply_stealth_async(page)
        
        print(f"Navigating to {url}")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(5)
        
        await page.screenshot(path="debug_provectus_listing.png")
        print("Screenshot saved to debug_provectus_listing.png")
        
        # Check for apply button
        apply_btn = await page.query_selector("a:has-text('Apply for this job'), button:has-text('Apply for this job')")
        if apply_btn:
            print("Found 'Apply for this job' button. Clicking...")
            await apply_btn.click()
            await asyncio.sleep(5)
            await page.screenshot(path="debug_provectus_form.png")
            print("Screenshot after click saved to debug_provectus_form.png")
            
            # Extract inputs
            inputs = await page.evaluate("""
                () => Array.from(document.querySelectorAll('input, select, textarea')).map(el => ({
                    id: el.id,
                    name: el.name,
                    type: el.type,
                    label: el.labels?.[0]?.innerText || el.placeholder || ""
                }))
            """)
            print(f"Found {len(inputs)} input elements on form page.")
            for i in inputs[:10]:
                print(f" - {i}")
        else:
            print("No 'Apply for this job' button found.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_page())
