import asyncio
from sqlalchemy import select
from database import AsyncSessionLocal
from models.user import User, JobPreference

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "testop@devapply.io"))
        user = result.scalar_one_or_none()
        if user:
            print(f"User: {user.full_name}")
            print(f"Bio: {user.bio}")
            pref_result = await db.execute(select(JobPreference).where(JobPreference.user_id == user.id))
            prefs = pref_result.scalar_one_or_none()
            if prefs:
                print(f"Job Titles: {prefs.job_titles}")
                print(f"Skills: {prefs.skills}")
                print(f"Exp Level: {prefs.experience_level}")
        else:
            print("Test user not found.")

if __name__ == "__main__":
    asyncio.run(main())
