"""
TheMemeCanvas Automation Suite — Scheduler Runner
=================================================
Configures and starts the APScheduler with all jobs.
Handles timezone-aware cron scheduling.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config.settings import settings

logger = logging.getLogger("thememecanvas.scheduler")

# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    """Return the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")
    return _scheduler


def init_scheduler() -> BackgroundScheduler:
    """
    Initialize and configure the APScheduler with all jobs.

    Returns:
        Configured BackgroundScheduler (not yet started).
    """
    global _scheduler

    tz = pytz.timezone(settings.timezone)
    logger.info("Initializing scheduler for timezone: %s", settings.timezone)

    _scheduler = BackgroundScheduler(
        timezone=tz,
        job_defaults={
            "misfire_grace_time": 3600,   # Allow jobs to run up to 1 hour late
            "coalesce": True,             # Merge missed runs into one
            "max_instances": 1,           # Only one instance of each job at a time
        },
    )

    # Parse upload time (HH:MM or multiple HH:MM,HH:MM)
    upload_times = [t.strip() for t in settings.upload_time.split(",") if t.strip()]
    health_hour, health_minute = _parse_time(settings.health_check_time)

    # --- Job 1: Daily Upload ---
    for idx, t_str in enumerate(upload_times):
        upload_hour, upload_minute = _parse_time(t_str)
        job_id = "daily_upload" if idx == 0 else f"daily_upload_{idx}"
        _scheduler.add_job(
            func=_safe_job_daily_upload,
            trigger=CronTrigger(hour=upload_hour, minute=upload_minute, timezone=tz),
            id=job_id,
            name=f"Daily Video Upload at {t_str}",
            replace_existing=True,
        )
        logger.info("Daily upload job '%s' scheduled for %02d:%02d %s", job_id, upload_hour, upload_minute, settings.timezone)

    # --- Job 2: Daily Health Check ---
    _scheduler.add_job(
        func=_safe_job_health_check,
        trigger=CronTrigger(hour=health_hour, minute=health_minute, timezone=tz),
        id="health_check",
        name="Daily Health Check",
        replace_existing=True,
    )
    logger.info("Health check scheduled for %02d:%02d %s", health_hour, health_minute, settings.timezone)

    # --- Job 3: Daily Summary (2 hours after the last upload time) ---
    last_upload_time = upload_times[-1] if upload_times else "21:00"
    last_hour, last_minute = _parse_time(last_upload_time)
    summary_hour = (last_hour + 2) % 24
    _scheduler.add_job(
        func=_safe_job_daily_summary,
        trigger=CronTrigger(hour=summary_hour, minute=last_minute, timezone=tz),
        id="daily_summary",
        name="Daily Summary Notification",
        replace_existing=True,
    )
    logger.info("Daily summary scheduled for %02d:%02d %s", summary_hour, last_minute, settings.timezone)

    # --- Job 4: Queue Sync (every hour) ---
    _scheduler.add_job(
        func=_safe_job_queue_sync,
        trigger=IntervalTrigger(hours=1),
        id="queue_sync",
        name="Hourly Queue Sync",
        replace_existing=True,
    )

    # --- Job 5: Empty Queue Check (every 6 hours) ---
    _scheduler.add_job(
        func=_safe_job_check_empty_queue,
        trigger=IntervalTrigger(hours=6),
        id="empty_queue_check",
        name="Empty Queue Checker",
        replace_existing=True,
    )

    # --- Job 6: Weekly Summary (Sunday evening) ---
    _scheduler.add_job(
        func=_safe_job_weekly_summary,
        trigger=CronTrigger(day_of_week="sun", hour=21, minute=30, timezone=tz),
        id="weekly_summary",
        name="Weekly Summary",
        replace_existing=True,
    )

    logger.info("Scheduler configured with %d jobs.", len(_scheduler.get_jobs()))
    return _scheduler


def start_scheduler() -> None:
    """Start the scheduler and notify."""
    global _scheduler

    if _scheduler is None:
        init_scheduler()

    _scheduler.start()

    # Get next run time for the upload job
    upload_job = _scheduler.get_job("daily_upload")
    next_run = upload_job.next_run_time.strftime("%Y-%m-%d %H:%M:%S %Z") if upload_job else "Unknown"

    logger.info("✅ Scheduler started. Next upload: %s", next_run)

    # Notify startup
    try:
        from app.database.base import db_session as get_db_session
        from app.services.notifications.dispatcher import NotificationDispatcher
        from app.services.drive.queue_manager import QueueManager

        notifier = NotificationDispatcher()
        with get_db_session() as db:
            queue = QueueManager()
            queue_size = queue.queue_size(db)

        notifier.notify_scheduler_started(
            next_upload_time=next_run,
            queue_size=queue_size,
            days_remaining=queue_size,
        )
    except Exception as e:
        logger.warning("Could not send startup notification: %s", e)


def stop_scheduler() -> None:
    """Gracefully stop the scheduler."""
    global _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped.")


def get_next_upload_time() -> Optional[str]:
    """Return the next scheduled upload time as a formatted string."""
    try:
        scheduler = get_scheduler()
        next_runs = []
        for job in scheduler.get_jobs():
            if (job.id == "daily_upload" or job.id.startswith("daily_upload_")) and job.next_run_time:
                next_runs.append(job.next_run_time)
        if next_runs:
            earliest = min(next_runs)
            return earliest.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        pass
    return None


def trigger_upload_now() -> None:
    """Force an immediate upload (skips the scheduled time)."""
    try:
        scheduler = get_scheduler()
        # Find the earliest upcoming job to trigger
        earliest_job = None
        earliest_time = None
        for job in scheduler.get_jobs():
            if job.id == "daily_upload" or job.id.startswith("daily_upload_"):
                if job.next_run_time:
                    if earliest_time is None or job.next_run_time < earliest_time:
                        earliest_time = job.next_run_time
                        earliest_job = job

        target_job = earliest_job or scheduler.get_job("daily_upload")
        if target_job:
            scheduler.modify_job(target_job.id, next_run_time=datetime.now())
            logger.info("Forced immediate upload triggered for job %s.", target_job.id)
        else:
            logger.error("No upload job found to trigger.")
    except Exception as e:
        logger.error("Failed to trigger immediate upload: %s", e)


def pause_uploads() -> None:
    """Pause all daily upload jobs."""
    try:
        scheduler = get_scheduler()
        paused_count = 0
        for job in scheduler.get_jobs():
            if job.id == "daily_upload" or job.id.startswith("daily_upload_"):
                scheduler.pause_job(job.id)
                paused_count += 1
        logger.info("Paused %d daily upload jobs.", paused_count)
    except Exception as e:
        logger.error("Failed to pause: %s", e)


def resume_uploads() -> None:
    """Resume all daily upload jobs."""
    try:
        scheduler = get_scheduler()
        resumed_count = 0
        for job in scheduler.get_jobs():
            if job.id == "daily_upload" or job.id.startswith("daily_upload_"):
                scheduler.resume_job(job.id)
                resumed_count += 1
        logger.info("Resumed %d daily upload jobs.", resumed_count)
    except Exception as e:
        logger.error("Failed to resume: %s", e)


def _parse_time(time_str: str) -> tuple[int, int]:
    """Parse 'HH:MM' string into (hour, minute) integers."""
    try:
        parts = time_str.split(":")
        return int(parts[0]), int(parts[1])
    except Exception:
        logger.warning("Invalid time format '%s'. Defaulting to 21:00.", time_str)
        return 21, 0


# ---------------------------------------------------------------------------
# Safe job wrappers (catches all exceptions to keep scheduler alive)
# ---------------------------------------------------------------------------

def _safe_job_daily_upload():
    try:
        from app.scheduler.jobs import job_daily_upload
        job_daily_upload()
    except Exception as e:
        logger.critical("FATAL: daily_upload job crashed: %s", e, exc_info=True)


def _safe_job_health_check():
    try:
        from app.scheduler.jobs import job_health_check
        job_health_check()
    except Exception as e:
        logger.error("health_check job crashed: %s", e, exc_info=True)


def _safe_job_daily_summary():
    try:
        from app.scheduler.jobs import job_daily_summary
        job_daily_summary()
    except Exception as e:
        logger.error("daily_summary job crashed: %s", e, exc_info=True)


def _safe_job_queue_sync():
    try:
        from app.scheduler.jobs import job_queue_sync
        job_queue_sync()
    except Exception as e:
        logger.error("queue_sync job crashed: %s", e, exc_info=True)


def _safe_job_check_empty_queue():
    try:
        from app.scheduler.jobs import job_check_empty_queue
        job_check_empty_queue()
    except Exception as e:
        logger.error("check_empty_queue job crashed: %s", e, exc_info=True)


def _safe_job_weekly_summary():
    try:
        from app.scheduler.jobs import job_weekly_summary
        job_weekly_summary()
    except Exception as e:
        logger.error("weekly_summary job crashed: %s", e, exc_info=True)
