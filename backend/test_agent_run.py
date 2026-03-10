import asyncio
import logging
from sqlalchemy import select
from database import AsyncSessionLocal
from models.user import User
from agent.orchestrator import run_agent_for_user

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_run():
    async with AsyncSessionLocal() as db:
        # Find our test user
        result = await db.execute(select(User).where(User.email == "testop@devapply.io"))
        user = result.scalar_one_or_none()
        
        if not user:
            print("Test user 'testop@devapply.io' not found in database. Please register first.")
            return

        print(f"Starting test run for user: {user.full_name} ({user.id})")
        await run_agent_for_user(str(user.id))
        print("Test run sequence completed.")

if __name__ == "__main__":
    asyncio.run(test_run())
