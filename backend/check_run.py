import asyncio
from sqlalchemy import select, desc
from database import AsyncSessionLocal
from models.application import AgentRun, Application

async def check_status():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AgentRun).order_by(desc(AgentRun.started_at)).limit(1)
        )
        run = result.scalar_one_or_none()
        if run:
            print(f"Run ID: {run.id}")
            print(f"Status: {run.status}")
            print(f"Jobs Found (So far): {run.total_jobs_found}")
            print(f"Applied: {run.total_applied}")
            print(f"Failed: {run.total_failed}")
            print("---")
            
        app_result = await db.execute(
            select(Application).where(Application.user_id == run.user_id).order_by(desc(Application.created_at)).limit(5)
        )
        apps = app_result.scalars().all()
        for app in apps:
            print(f"App: {app.company_name} - {app.job_title} ({app.status})")

if __name__ == "__main__":
    asyncio.run(check_status())
