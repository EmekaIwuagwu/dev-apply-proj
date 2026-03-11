import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def start_scheduler() -> AsyncIOScheduler:
    from agent.orchestrator import run_agent_for_all_users

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_agent_for_all_users,
        trigger=CronTrigger(hour=6, minute=0),  # 06:00 UTC daily
        id="devapply_daily_run",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.start()
    logger.info("Scheduler started — daily agent run at 06:00 UTC")
    return scheduler
