import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.services.email_service import send_daily_summaries

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _daily_email_job():
    async with AsyncSessionLocal() as db:
        count = await send_daily_summaries(db)
        await db.commit()
        logger.info("Scheduled daily email sent to %d users", count)


def start_scheduler():
    settings = get_settings()
    scheduler.add_job(
        _daily_email_job,
        trigger="cron",
        hour=settings.DAILY_EMAIL_HOUR,
        minute=0,
        id="daily_email",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started, daily email set for %s:00", settings.DAILY_EMAIL_HOUR)
