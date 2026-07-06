"""
TheMemeCanvas Automation Suite — Scheduler Job Definitions
==========================================================
Defines all APScheduler jobs:
    1. Daily upload at configured time (default 9:00 PM)
    2. Daily health check at configured time (default 8:00 AM)
    3. Daily summary notification
    4. Weekly summary notification
    5. Monthly summary notification
    6. Queue sync (hourly)
    7. Queue empty check (every 6 hours when queue is empty)
"""

from __future__ import annotations

import logging
from datetime import datetime, date

from app.config.settings import settings
from app.utils.health_check import run_full_health_check

logger = logging.getLogger("thememecanvas.scheduler")


def job_daily_upload() -> None:
    """
    Main daily upload job — picks and uploads the next video from the queue.
    Triggered at the configured UPLOAD_TIME.
    """
    logger.info("=" * 50)
    logger.info("🕒 Daily upload job triggered at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 50)

    if settings.uploads_paused:
        logger.info("Uploads are paused. Skipping daily upload.")
        return

    try:
        from app.workflows.upload_pipeline import UploadPipeline
        pipeline = UploadPipeline()
        success = pipeline.run()

        if success:
            logger.info("✅ Daily upload job completed successfully.")
        else:
            logger.warning("⚠️ Daily upload job completed with issues.")

    except Exception as e:
        logger.error("❌ Daily upload job crashed: %s", e, exc_info=True)

        # Notify crash
        try:
            from app.services.notifications.dispatcher import NotificationDispatcher
            from app.services.notifications.base import NotificationLevel

            notifier = NotificationDispatcher()
            notifier.dispatch(
                f"Daily upload job crashed!\n\nError: {str(e)[:500]}",
                level=NotificationLevel.CRITICAL,
                title="🚨 Upload Job Crashed!",
                event_type="job_crashed",
            )
        except Exception as notify_exc:
            logger.error("Failed to send crash notification: %s", notify_exc)


def job_health_check() -> None:
    """
    Daily health check — verifies all services are operational.
    Triggered each morning at HEALTH_CHECK_TIME.
    """
    logger.info("🩺 Running daily health check...")

    try:
        report = run_full_health_check()

        if not report.is_healthy:
            from app.services.notifications.dispatcher import NotificationDispatcher
            from app.services.notifications.base import NotificationLevel

            notifier = NotificationDispatcher()

            failed_components = [r for r in report.results if not r.is_healthy]
            for result in failed_components:
                notifier.notify_health_check_failed(
                    component=result.component,
                    error=result.message,
                )

        logger.info(
            "Health check complete: %s (%d/%d healthy)",
            report.overall_status,
            sum(1 for r in report.results if r.is_healthy),
            len(report.results),
        )

    except Exception as e:
        logger.error("Health check job crashed: %s", e, exc_info=True)


def job_daily_summary() -> None:
    """
    Send a daily summary notification with today's upload status.
    Triggered shortly after the upload window (e.g., 11:00 PM).
    """
    logger.info("📊 Generating daily summary...")

    try:
        from app.database.base import db_session as get_db_session
        from app.models.upload import Upload
        from app.config.constants import UploadStage

        with get_db_session() as db:
            today = date.today()

            # Today's upload
            today_upload = (
                db.query(Upload)
                .filter(
                    Upload.completed_at >= datetime(today.year, today.month, today.day),
                    Upload.status == UploadStage.COMPLETED,
                )
                .first()
            )

            # Stats
            total_uploaded = db.query(Upload).filter(Upload.status == UploadStage.COMPLETED).count()
            total_failed = db.query(Upload).filter(Upload.status == UploadStage.FAILED).count()

            # Queue remaining
            from app.services.drive.queue_manager import QueueManager
            queue = QueueManager()
            queue_remaining = queue.queue_size(db)

            from app.services.notifications.dispatcher import NotificationDispatcher

            notifier = NotificationDispatcher()
            notifier.notify_daily_summary(
                date=today.strftime("%A, %B %d, %Y"),
                filename=today_upload.filename if today_upload else "No upload today",
                title=today_upload.title if today_upload else "—",
                youtube_status=today_upload.youtube_status if today_upload else "—",
                queue_remaining=queue_remaining,
                days_remaining=queue_remaining,
                next_upload_time=settings.upload_time,
                total_uploaded=total_uploaded,
                total_failed=total_failed,
                db_session=db,
            )

    except Exception as e:
        logger.error("Daily summary job failed: %s", e, exc_info=True)


def job_queue_sync() -> None:
    """
    Sync Drive queue folder to local database.
    Runs hourly to discover newly added videos.
    """
    logger.info("🔄 Running queue sync...")

    try:
        from app.database.base import db_session as get_db_session
        from app.services.drive.queue_manager import QueueManager

        with get_db_session() as db:
            queue = QueueManager()
            new_count, total = queue.sync_queue_to_db(db)
            logger.info("Queue sync complete: +%d new, %d total.", new_count, total)

    except Exception as e:
        logger.error("Queue sync job failed: %s", e, exc_info=True)


def job_check_empty_queue() -> None:
    """
    Periodically check if the queue has new videos when it was empty.
    Runs every 6 hours. Sends notification if new videos are found.
    """
    logger.info("🔍 Checking for new videos in empty queue...")

    try:
        from app.database.base import db_session as get_db_session
        from app.services.drive.queue_manager import QueueManager
        from app.services.notifications.dispatcher import NotificationDispatcher
        from app.services.notifications.base import NotificationLevel

        with get_db_session() as db:
            queue = QueueManager()
            new_count, total = queue.sync_queue_to_db(db)

            if new_count > 0:
                notifier = NotificationDispatcher()
                notifier.dispatch(
                    f"🆕 {new_count} new video(s) added to the queue!\n"
                    f"Total in queue: {total}\n"
                    f"Next upload: Today at {settings.upload_time}",
                    level=NotificationLevel.SUCCESS,
                    title="New Videos Detected!",
                    event_type="new_videos_detected",
                    db_session=db,
                )

    except Exception as e:
        logger.error("Empty queue check job failed: %s", e, exc_info=True)


def job_weekly_summary() -> None:
    """Send a weekly performance summary every Sunday at 9:00 PM."""
    logger.info("📈 Generating weekly summary...")

    try:
        from datetime import timedelta
        from app.database.base import db_session as get_db_session
        from app.models.upload import Upload
        from app.config.constants import UploadStage
        from app.services.notifications.dispatcher import NotificationDispatcher
        from app.services.notifications.base import NotificationLevel

        with get_db_session() as db:
            week_ago = datetime.utcnow() - timedelta(days=7)

            weekly_uploads = (
                db.query(Upload)
                .filter(
                    Upload.completed_at >= week_ago,
                    Upload.status == UploadStage.COMPLETED,
                )
                .count()
            )

            weekly_failed = (
                db.query(Upload)
                .filter(
                    Upload.created_at >= week_ago,
                    Upload.status == UploadStage.FAILED,
                )
                .count()
            )

            from app.services.drive.queue_manager import QueueManager
            queue = QueueManager()
            queue_remaining = queue.queue_size(db)

            msg = (
                f"📈 *Weekly Summary — TheMemeCanvas*\n\n"
                f"📅 Week ending: {date.today().strftime('%B %d, %Y')}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Videos uploaded this week: {weekly_uploads}\n"
                f"❌ Failed uploads: {weekly_failed}\n"
                f"📦 Queue remaining: {queue_remaining}\n"
                f"⏳ Est. days remaining: {queue_remaining}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Keep grinding! 🎭"
            )

            notifier = NotificationDispatcher()
            notifier.dispatch(
                msg,
                level=NotificationLevel.INFO,
                title="📈 Weekly Summary",
                event_type="weekly_summary",
                db_session=db,
            )

    except Exception as e:
        logger.error("Weekly summary job failed: %s", e, exc_info=True)
