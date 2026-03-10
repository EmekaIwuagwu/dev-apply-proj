import asyncio
import logging
import base64
from sqlalchemy import select
from database import AsyncSessionLocal
from models.user import User, JobPreference
from agent.phases.execute import ExecutePhase
from dataclasses import dataclass

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MockJob:
    title: str
    company: str
    url: str
    match_score: float = 95.0
    reasoning: str = "Perfect match for backend testing."
    cover_note: str = "Hi, I'm a test bot. Please ignore this application."

async def test_apply():
    async with AsyncSessionLocal() as db:
        # Get the test user
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        
        if not user:
            print("No user found in DB. Please run seed or create a user first.")
            return

        # Ensure user has a valid-ish resume for the test
        if not user.resume_base64:
            # Simple dummy PDF base64 (not valid PDF but should be enough for 'upload' test if we don't check content)
            user.resume_base64 = base64.b64encode(b"%PDF-1.4 test content").decode('utf-8')
            user.resume_filename = "test_resume.pdf"
            await db.commit()

        # Target URL found by subagent
        target_url = "https://jobs.lever.co/provectus/cbd7d5f6-b565-4225-854a-08c5b9a66097"
        job = MockJob(
            title="Senior Python Developer",
            company="Provectus",
            url=target_url
        )

        print(f"--- Starting Application Test for {user.full_name} ---")
        print(f"Target: {job.title} at {job.company}")
        print(f"URL: {job.url}")

        executor = ExecutePhase(user, [job])
        
        # We manually call _apply_to_job to avoid the 'resting' period in execute()
        from playwright.async_api import async_playwright
        from playwright_stealth import Stealth
        import os
        from pathlib import Path

        async with async_playwright() as p:
            profile_dir = Path(__file__).parent / "agent" / "browser" / "profiles" / str(user.id)
            os.makedirs(profile_dir, exist_ok=True)
            
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False, # Set to False so we can see it (if we had a display, but here we'll just rely on screenshots)
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            # Mask fingerprint indicators
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
                Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            """)

            result = await executor._apply_to_job(context, job)
            
            print(f"--- Application Result ---")
            print(f"Status: {result.get('status')}")
            print(f"Error: {result.get('error')}")
            
            # Take a final screenshot of the result
            pages = context.pages
            if pages:
                await pages[0].screenshot(path="final_application_result.png")
                print("Final screenshot saved to final_application_result.png")

            await context.close()

if __name__ == "__main__":
    asyncio.run(test_apply())
