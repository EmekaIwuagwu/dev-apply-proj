import asyncio
from sqlalchemy import select
from database import AsyncSessionLocal
from models.application import AgentRun

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(1))
        run = result.scalar_one_or_none()
        if run:
            print(f"--- Log for Run {run.id} ({run.status}) ---")
            print(run.log_output)
        else:
            print("No agent runs found.")

if __name__ == "__main__":
    asyncio.run(main())
