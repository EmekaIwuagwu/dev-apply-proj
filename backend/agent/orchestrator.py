import asyncio
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal
from models.user import User, JobPreference
from models.application import AgentRun, Application
from agent.phases.read import ReadPhase
from agent.phases.plan import PlanPhase
from agent.phases.execute import ExecutePhase

logger = logging.getLogger(__name__)

async def run_agent_for_all_users():
    """
    Entry point for the daily agent run.
    """
    async with AsyncSessionLocal() as db:
        # Get all users who have the agent enabled
        result = await db.execute(select(User).where(User.agent_enabled == True, User.is_active == True))
        users = result.scalars().all()
        
        logger.info(f"Starting agent run for {len(users)} users")
        
        tasks = [run_agent_for_user(user.id) for user in users]
        await asyncio.gather(*tasks, return_exceptions=True)

async def run_agent_for_user(user_id: str):
    """
    Coordinates the full 3-phase loop for a single user.
    """
    async with AsyncSessionLocal() as db:
        # Fetch user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user: return

        # Fetch preferences
        pref_result = await db.execute(
            select(JobPreference).where(JobPreference.user_id == user_id)
        )
        preferences = pref_result.scalar_one_or_none()

        # Create agent_run record
        run = AgentRun(
            user_id=user.id,
            status="running",
            started_at=datetime.utcnow()
        )
        db.add(run)
        await db.commit()

        log_buf = []
        def log_event(msg):
            formatted = f"[{datetime.utcnow().strftime('%H:%M:%S')}] {msg}"
            log_buf.append(formatted)
            logger.info(f"User {user.id}: {msg}")

        try:
            log_event("Wakeup sequence initiated.")
            
            if not preferences:
                log_event("No job preferences found. Skipping run.")
                run.status = "skipped"
                await db.commit()
                return

            # PHASE 1: READ
            log_event("Starting PHASE 1: READ (Job Discovery)")
            reader = ReadPhase(user, preferences)
            raw_jobs = await reader.execute()
            log_event(f"Discovery complete. Found {len(raw_jobs)} potential listings.")
            run.total_jobs_found = len(raw_jobs)
            
            # PHASE 2: PLAN
            log_event("Starting PHASE 2: PLAN (Analyze & Strategy)")
            planner = PlanPhase(user, raw_jobs)
            planned_jobs = await planner.execute()
            log_event(f"Strategy complete. {len(planned_jobs)} jobs scheduled for application.")
            
            # PHASE 3: EXECUTE
            log_event("Starting PHASE 3: EXECUTE (Browser Automation)")
            executor = ExecutePhase(user, planned_jobs)
            results = await executor.execute()
            
            # Record Results
            total_applied = 0
            total_failed = 0
            for res in results:
                if res['status'] == 'submitted':
                    total_applied += 1
                else:
                    total_failed += 1
                    
                # Store application in DB
                db_app = Application(
                    user_id=user.id,
                    job_title=res['job'].title,
                    company_name=res['job'].company,
                    job_url=res['job'].url,
                    status=res['status'],
                    ai_match_score=res['job'].match_score,
                    ai_reasoning=res['job'].reasoning,
                    cover_note=res['job'].cover_note,
                    applied_at=datetime.utcnow() if res['status'] == 'submitted' else None
                )
                db.add(db_app)

            run.total_applied = total_applied
            run.total_failed = total_failed
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.log_output = "\n".join(log_buf)
            log_event(f"Run complete. Total Applied: {total_applied}, Total Failed: {total_failed}")

        except Exception as e:
            logger.error(f"Agent run failed for user {user.id}: {str(e)}")
            run.status = "failed"
            run.log_output = "\n".join(log_buf) + f"\n[ERROR] {str(e)}"
            run.completed_at = datetime.utcnow()
        
        await db.commit()
