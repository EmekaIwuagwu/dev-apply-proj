import asyncio
from typing import List
from agent.phases.read import RawJob
from database import AsyncSessionLocal
from models.user import User, JobPreference
from agent.phases.plan import PlanPhase
from agent.phases.execute import ExecutePhase
from sqlalchemy import select

async def manual_agent_run():
    # HIGH QUALITY MOCK JOBS
    mock_jobs = [
        RawJob(
            title="Senior Fullstack Engineer (Python/React)",
            company="Open Energy Transition",
            url="https://jobs.lever.co/lever/13606b12-9844-4861-9c64-4e78f9435b5a",
            description="""
            We are looking for a Senior Fullstack Engineer to build the future of energy.
            Required Skills:
            - Python, FastAPI, PostgreSQL
            - React, TypeScript, TailwindCSS
            - AWS and Docker experience
            - 5+ years of experience in technical roles.
            This is a remote-first position.
            """,
            platform="Lever",
            location="Remote"
        )
    ]

    async with AsyncSessionLocal() as db:
        # Fetch user
        result = await db.execute(select(User).where(User.email == "testop@devapply.io"))
        user = result.scalar_one_or_none()
        if not user:
            print("User not found")
            return

        # EXPLICITLY ATTACH PREFERENCES (to avoid PlanPhase failing to see them)
        pref_result = await db.execute(select(JobPreference).where(JobPreference.user_id == user.id))
        user.job_preferences = pref_result.scalar_one_or_none()

        print(f"--- STARTING MOCK RUN FOR {user.full_name} ---")
        print(f"Bio: {user.bio}")
        print(f"Preferences: {user.job_preferences.job_titles if user.job_preferences else 'NONE'}")
        print(f"Phase 1: (Manual Inject) Found {len(mock_jobs)} high-quality job.")

        # Phase 2: Plan
        print("Phase 2: PLAN (Analyzing Match with Gemini)...")
        planner = PlanPhase(user, mock_jobs)
        planned_jobs = await planner.execute()
        print(f"Plan complete. Found {len(planned_jobs)} matches.")

        if not planned_jobs:
            print("No jobs matched well enough to proceed. Check if GPT/Gemini output reasoning.")
            return

        for pj in planned_jobs:
            print(f" - [{pj.match_score}%] {pj.title}")
            
        # Phase 3: Execute (Testing ONLY the first one)
        print("\nPhase 3: EXECUTE (Starting Browser Automation - FILLING ONLY)...")
        # I'll modify ExecutePhase to be safer for testing (not submitting) if I can, 
        # but for now let's just run it. 
        
        executor = ExecutePhase(user, [planned_jobs[0]])
        results = await executor.execute()
        
        for res in results:
            print(f"RESULT: {res['job'].title} -> {res['status']}")

if __name__ == "__main__":
    asyncio.run(manual_agent_run())
