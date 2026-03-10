import asyncio
from sqlalchemy import select
from database import AsyncSessionLocal
from models.user import User, JobPreference

async def seed_prefs():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "testop@devapply.io"))
        user = result.scalar_one_or_none()
        
        if not user:
            print("User not found")
            return

        # Check if prefs exist
        pref_result = await db.execute(select(JobPreference).where(JobPreference.user_id == user.id))
        prefs = pref_result.scalar_one_or_none()
        
        if not prefs:
            prefs = JobPreference(user_id=user.id)
            db.add(prefs)
        
        prefs.job_titles = ["Fullstack Engineer", "Back-end Developer", "Python Developer"]
        prefs.skills = ["Python", "React", "FastAPI", "PostgreSQL", "AWS"]
        prefs.experience_level = "Mid-Senior"
        prefs.job_type = "Full-time"
        prefs.preferred_locations = ["Remote", "Europe", "US"]
        
        await db.commit()
        print(f"Successfully seeded job preferences for {user.email}")

if __name__ == "__main__":
    asyncio.run(seed_prefs())
