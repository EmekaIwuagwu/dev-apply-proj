import asyncio
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models.application import AgentRun, Application
from models.user import JobPreference, User
from agent.phases.execute import ExecutePhase
from agent.phases.plan import PlanPhase
from agent.phases.read import ReadPhase

logger = logging.getLogger(__name__)


async def run_agent_for_all_users() -> None:
    """Entry point for the daily scheduled agent run."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(
                User.agent_enabled == True,
                User.is_active == True,
            )
        )
        users = result.scalars().all()
        logger.info(f"Starting agent run for {len(users)} user(s).")

        tasks = [run_agent_for_user(user.id) for user in users]
        await asyncio.gather(*tasks, return_exceptions=True)


async def run_agent_for_user(user_id: str) -> None:
    """
    Coordinates the full 3-phase pipeline for a single user:
      Phase 1 — READ   : Discover jobs via strategy-driven search
      Phase 2 — PLAN   : Score & filter with Gemini
      Phase 3 — EXECUTE: Fill & submit application forms
    """
    async with AsyncSessionLocal() as db:
        # ---- Fetch user ----
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            logger.warning(f"User {user_id} not found — skipping.")
            return

        # ---- Fetch preferences ----
        pref_result = await db.execute(
            select(JobPreference).where(JobPreference.user_id == user_id)
        )
        preferences = pref_result.scalar_one_or_none()

        # ---- Create AgentRun record ----
        run = AgentRun(
            user_id=user.id,
            status="running",
            started_at=datetime.utcnow(),
        )
        db.add(run)
        await db.commit()

        log_buf = []

        def log_event(msg: str) -> None:
            formatted = f"[{datetime.utcnow().strftime('%H:%M:%S')}] {msg}"
            log_buf.append(formatted)
            logger.info(f"User {user.id}: {msg}")

        try:
            log_event("Wakeup sequence initiated.")

            if not preferences:
                log_event("No job preferences configured — skipping run.")
                run.status = "skipped"
                await db.commit()
                return

            # ----------------------------------------------------------
            # PHASE 1: READ — job discovery
            # ----------------------------------------------------------
            log_event("PHASE 1: READ — starting job discovery …")
            reader = ReadPhase(user, preferences)
            raw_jobs = await reader.execute()
            log_event(f"Discovery complete — {len(raw_jobs)} potential listing(s) found.")
            run.total_jobs_found = len(raw_jobs)

            if not raw_jobs:
                log_event("No jobs discovered — ending run early.")
                run.status = "completed"
                run.completed_at = datetime.utcnow()
                run.log_output = "\n".join(log_buf)
                await db.commit()
                return

            # ----------------------------------------------------------
            # PHASE 2: PLAN — LLM scoring & filtering
            # ----------------------------------------------------------
            log_event("PHASE 2: PLAN — analysing & scoring jobs …")
            planner = PlanPhase(user, raw_jobs, preferences)   # preferences passed
            planned_jobs = await planner.execute()
            log_event(
                f"Planning complete — {len(planned_jobs)} job(s) scheduled for application."
            )

            if not planned_jobs:
                log_event("No jobs passed the match threshold — ending run.")
                run.status = "completed"
                run.total_skipped = len(raw_jobs)
                run.completed_at = datetime.utcnow()
                run.log_output = "\n".join(log_buf)
                await db.commit()
                return

            # ----------------------------------------------------------
            # PHASE 3: EXECUTE — browser automation
            # ----------------------------------------------------------
            log_event("PHASE 3: EXECUTE — starting browser automation …")
            executor = ExecutePhase(user, planned_jobs, preferences)  # preferences passed
            results = await executor.execute()

            # ---- Record results ----
            total_applied = 0
            total_failed = 0
            total_skipped = 0

            for res in results:
                status = res.get("status", "failed")
                job = res["job"]

                if status == "submitted":
                    total_applied += 1
                elif status == "skipped":
                    total_skipped += 1
                else:
                    total_failed += 1

                db_app = Application(
                    user_id=user.id,
                    job_title=job.title,
                    company_name=job.company,
                    job_url=job.url,
                    job_description=job.description[:2000] if job.description else None,
                    platform=job.platform,
                    status=status,
                    ai_match_score=job.match_score,
                    ai_reasoning=job.reasoning,
                    cover_note=job.cover_note,
                    error_message=res.get("error"),
                    applied_at=datetime.utcnow() if status == "submitted" else None,
                )
                db.add(db_app)

            run.total_applied = total_applied
            run.total_skipped = total_skipped
            run.total_failed = total_failed
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.log_output = "\n".join(log_buf)
            log_event(
                f"Run complete — Applied: {total_applied}, "
                f"Skipped: {total_skipped}, Failed: {total_failed}"
            )

        except Exception as e:
            logger.error(f"Agent run failed for user {user.id}: {e}", exc_info=True)
            run.status = "failed"
            run.completed_at = datetime.utcnow()
            run.log_output = "\n".join(log_buf) + f"\n[ERROR] {e}"

        await db.commit()
