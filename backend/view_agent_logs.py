import asyncio
from sqlalchemy import select
from database import AsyncSessionLocal
from models.application import AgentRun

async def view_logs():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(1))
        run = result.scalar_one_or_none()
        if run:
            print("=== LATEST AGENT RUN LOGS ===")
            print(f"Status: {run.status}")
            print(f"Jobs Found: {run.total_jobs_found}")
            print(f"Applied: {run.total_applied}")
            print(f"Failed: {run.total_failed}")
            print("-" * 30)
            print(run.log_output)
        else:
            print("No agent runs found.")

if __name__ == "__main__":
    asyncio.run(view_logs())
