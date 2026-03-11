"""
orchestrator.py — Coordinates the three-phase agent pipeline per user.

Phase 1 — SEARCH   : Open browser, search DDG, collect Lever/Ashby job URLs
Phase 2 — READ     : Visit each URL, scroll through, AI Eye reads + scores
Phase 3 — APPLY    : Fill forms visually, submit, confirm success

The agent runs inside one persistent browser context per user so cookies
and sessions survive across daily runs (avoids re-login challenges).
"""
import logging
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright
from sqlalchemy import select

from config import TIER_DAILY_LIMITS, get_daily_limit
from database import AsyncSessionLocal
from models.application import AgentRun, Application
from models.user import JobPreference, User

logger = logging.getLogger(__name__)

_PROFILES_DIR = Path(__file__).parent / "profiles"


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

async def run_agent_for_all_users() -> None:
    """Scheduled daily run — processes every enabled user."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.agent_enabled.is_(True), User.is_active.is_(True))
        )
        users = result.scalars().all()

    logger.info(f"Daily run: {len(users)} user(s)")
    for user in users:
        try:
            await run_agent_for_user(str(user.id))
        except Exception as e:
            logger.error(f"Agent run failed for {user.id}: {e}", exc_info=True)


async def run_agent_for_user(user_id: str) -> None:
    """Full 3-phase pipeline for one user."""
    async with AsyncSessionLocal() as db:
        u = await db.execute(select(User).where(User.id == user_id))
        user = u.scalar_one_or_none()
        if not user:
            logger.warning(f"User {user_id} not found")
            return

        p = await db.execute(select(JobPreference).where(JobPreference.user_id == user_id))
        preferences = p.scalar_one_or_none()

        # Check tier daily limit
        daily_limit = get_daily_limit(user.tier)

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
        logger.info(f"[{getattr(user, 'email', user_id)}] {msg}")

    try:
        emit("Agent starting — initialising browser …")

        if not preferences or not getattr(preferences, "job_titles", None):
            emit("No job preferences configured — run skipped.")
            await _finish_run(run, "skipped", log)
            return

        profile_dir = str(_PROFILES_DIR / str(user.id))
        seed = str(user.id)

        async with async_playwright() as pw:
            from agent.browser.context import new_context
            from agent.vision.ai_eye import AIEye

            ctx = await new_context(pw, profile_dir)
            eye = AIEye()

            try:
                # ----------------------------------------------------------
                # PHASE 1 — SEARCH
                # ----------------------------------------------------------
                emit("PHASE 1 — Searching for jobs …")
                from agent.phases.searcher import find_jobs
                raw_jobs = await find_jobs(ctx, user, preferences, eye, seed)
                emit(f"Found {len(raw_jobs)} job listing(s) to evaluate.")

                async with AsyncSessionLocal() as db:
                    run.total_jobs_found = len(raw_jobs)
                    await db.merge(run)
                    await db.commit()

                if not raw_jobs:
                    emit("No jobs found — ending run.")
                    await _finish_run(run, "completed", log)
                    return

                # ----------------------------------------------------------
                # PHASE 2 — READ / EVALUATE
                # ----------------------------------------------------------
                emit("PHASE 2 — Reading and evaluating job listings …")
                from agent.phases.reader import evaluate_jobs
                good_jobs = await evaluate_jobs(ctx, raw_jobs, user, preferences, eye, seed)
                emit(f"{len(good_jobs)} job(s) passed evaluation (score ≥ 70).")

                if not good_jobs:
                    emit("No jobs passed evaluation — ending run.")
                    async with AsyncSessionLocal() as db:
                        run.total_skipped = len(raw_jobs)
                        await db.merge(run)
                        await db.commit()
                    await _finish_run(run, "completed", log)
                    return

                # Apply daily tier limit
                if daily_limit is not None:
                    good_jobs = good_jobs[:daily_limit]
                    emit(f"Tier limit applied: applying to {len(good_jobs)} job(s).")

                # ----------------------------------------------------------
                # PHASE 3 — APPLY
                # ----------------------------------------------------------
                emit("PHASE 3 — Applying to jobs …")
                from agent.phases.applicator import apply_to_jobs
                results = await apply_to_jobs(ctx, good_jobs, user, preferences, eye, seed)

            finally:
                await ctx.close()

        # ------------------------------------------------------------------
        # Record results
        # ------------------------------------------------------------------
        n_submitted = n_skipped = n_failed = 0
        from agent.notifications.service import send_success_email

        async with AsyncSessionLocal() as db:
            for res in results:
                status = res["status"]
                job = res["job"]

                if status == "submitted":
                    n_submitted += 1
                elif status == "skipped":
                    n_skipped += 1
                else:
                    n_failed += 1

                app = Application(
                    user_id=user.id,
                    job_title=job.title,
                    company_name=job.company,
                    job_url=job.url,
                    job_description=(job.description or "")[:2000],
                    platform=job.platform,
                    status=status,
                    ai_match_score=job.score / 100.0,
                    ai_reasoning=job.reasoning,
                    cover_note=job.cover_note,
                    error_message=res.get("error"),
                    applied_at=datetime.utcnow() if status == "submitted" else None,
                )
                db.add(app)

            run.total_applied = n_submitted
            run.total_skipped = n_skipped
            run.total_failed = n_failed
            await db.merge(run)
            await db.commit()

        # Send email notifications for successful applications
        for res in results:
            if res["status"] == "submitted":
                job = res["job"]
                emit(f"Submitted: {job.title} @ {job.company} [{job.score}%]")
                try:
                    await send_success_email(
                        user_email=user.email,
                        user_full_name=user.full_name,
                        user_salutation=user.salutation,
                        job_title=job.title,
                        company_name=job.company,
                        job_url=job.url,
                        match_score=job.score / 100.0,
                        applied_at=datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC"),
                        cover_note=job.cover_note,
                    )
                except Exception as email_err:
                    logger.warning(f"Email notification failed: {email_err}")

        emit(
            f"Run complete — Submitted: {n_submitted}, "
            f"Skipped: {n_skipped}, Failed: {n_failed}"
        )
        await _finish_run(run, "completed", log)

    except Exception as e:
        logger.error(f"Pipeline crashed for {getattr(user, 'email', user_id)}: {e}", exc_info=True)
        log.append(f"[FATAL] {e}")
        await _finish_run(run, "failed", log)


async def _finish_run(run: AgentRun, status: str, log: list[str]) -> None:
    async with AsyncSessionLocal() as db:
        run.status = status
        run.completed_at = datetime.utcnow()
        run.log_output = "\n".join(log)
        await db.merge(run)
        await db.commit()
