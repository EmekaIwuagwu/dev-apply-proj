"""
Orchestrator — coordinates the 3-phase pipeline for a single user:

  Phase 1 — SEARCH  : Discover job listings via DDG (Lever + Ashby)
  Phase 2 — PLAN    : Score & filter jobs with Gemini
  Phase 3 — APPLY   : Fill and submit application forms
"""
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from database import AsyncSessionLocal
from models.application import AgentRun, Application
from models.user import JobPreference, User

logger = logging.getLogger(__name__)

_PROFILES_DIR = Path(__file__).parent / "profiles"


async def run_agent_for_all_users() -> None:
    """Entry point for the daily scheduled run — processes all enabled users."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.agent_enabled == True, User.is_active == True)
        )
        users = result.scalars().all()

    logger.info(f"Daily run: {len(users)} user(s) to process")
    for user in users:
        try:
            await run_agent_for_user(str(user.id))
        except Exception as e:
            logger.error(f"Agent run failed for user {user.id}: {e}", exc_info=True)


async def run_agent_for_user(user_id: str) -> None:
    """Full pipeline for one user — creates an AgentRun record, then runs all 3 phases."""
    async with AsyncSessionLocal() as db:
        # Load user
        u_result = await db.execute(select(User).where(User.id == user_id))
        user = u_result.scalar_one_or_none()
        if not user:
            logger.warning(f"User {user_id} not found")
            return

        # Load preferences
        p_result = await db.execute(
            select(JobPreference).where(JobPreference.user_id == user_id)
        )
        preferences = p_result.scalar_one_or_none()

        # Create run record
        run = AgentRun(
            user_id=user.id,
            status="running",
            started_at=datetime.utcnow(),
        )
        db.add(run)
        await db.commit()

        log: list[str] = []

        def emit(msg: str) -> None:
            ts = datetime.utcnow().strftime("%H:%M:%S")
            log.append(f"[{ts}] {msg}")
            logger.info(f"[{user.email}] {msg}")

        try:
            emit("Agent wakeup.")

            if not preferences or not getattr(preferences, "job_titles", None):
                emit("No job preferences configured — skipping.")
                run.status = "skipped"
                run.completed_at = datetime.utcnow()
                run.log_output = "\n".join(log)
                await db.commit()
                return

            profile_dir = str(_PROFILES_DIR / str(user.id))

            # ----------------------------------------------------------
            # PHASE 1 — SEARCH
            # ----------------------------------------------------------
            emit("PHASE 1: Searching for jobs …")
            from agent.search import discover_jobs
            raw_jobs = await discover_jobs(user, preferences, profile_dir)
            emit(f"Found {len(raw_jobs)} job listing(s).")
            run.total_jobs_found = len(raw_jobs)
            await db.commit()

            if not raw_jobs:
                emit("No jobs found — ending run.")
                run.status = "completed"
                run.completed_at = datetime.utcnow()
                run.log_output = "\n".join(log)
                await db.commit()
                return

            # ----------------------------------------------------------
            # PHASE 2 — PLAN
            # ----------------------------------------------------------
            emit("PHASE 2: Scoring jobs …")
            from agent.planner import plan_jobs
            planned = await plan_jobs(user, raw_jobs, preferences)
            emit(f"{len(planned)} job(s) passed the match threshold.")

            if not planned:
                emit("No jobs passed scoring — ending run.")
                run.status = "completed"
                run.total_skipped = len(raw_jobs)
                run.completed_at = datetime.utcnow()
                run.log_output = "\n".join(log)
                await db.commit()
                return

            # ----------------------------------------------------------
            # PHASE 3 — APPLY
            # ----------------------------------------------------------
            emit("PHASE 3: Applying to jobs …")
            from agent.applicator import Applicator
            applicator = Applicator(user, preferences, profile_dir)
            results = await applicator.run(planned)

            # Record results
            n_submitted = n_skipped = n_failed = 0
            from agent.notifications.service import send_success_email

            for res in results:
                status = res["status"]
                job = res["job"]

                if status == "submitted":
                    n_submitted += 1
                elif status == "skipped":
                    n_skipped += 1
                else:
                    n_failed += 1

                db_app = Application(
                    user_id=user.id,
                    job_title=job.title,
                    company_name=job.company,
                    job_url=job.url,
                    job_description=(job.description or "")[:2000],
                    platform=job.platform,
                    status=status,
                    ai_match_score=job.match_score,
                    ai_reasoning=job.reasoning,
                    cover_note=job.cover_note,
                    error_message=res.get("error"),
                    applied_at=datetime.utcnow() if status == "submitted" else None,
                )
                db.add(db_app)

                if status == "submitted":
                    emit(f"Submitted: {job.title} @ {job.company}")
                    try:
                        await send_success_email(
                            user_email=user.email,
                            user_full_name=user.full_name,
                            user_salutation=user.salutation,
                            job_title=job.title,
                            company_name=job.company,
                            job_url=job.url,
                            match_score=job.match_score / 100,
                            applied_at=datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC"),
                            cover_note=job.cover_note,
                        )
                    except Exception as email_err:
                        logger.warning(f"Email failed: {email_err}")

            run.total_applied = n_submitted
            run.total_skipped = n_skipped
            run.total_failed = n_failed
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            emit(
                f"Run complete — Submitted: {n_submitted}, "
                f"Skipped: {n_skipped}, Failed: {n_failed}"
            )

        except Exception as e:
            logger.error(f"Pipeline failed for {user.email}: {e}", exc_info=True)
            run.status = "failed"
            run.completed_at = datetime.utcnow()
            log.append(f"[ERROR] {e}")

        run.log_output = "\n".join(log)
        await db.commit()
