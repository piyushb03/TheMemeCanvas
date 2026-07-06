"""
TheMemeCanvas Automation Suite — Notification Dispatcher
=========================================================
Fan-out notifications to all configured providers.
Logs every notification attempt to the database.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from app.config.settings import settings
from app.services.notifications.base import BaseNotificationProvider, NotificationLevel

logger = logging.getLogger("thememecanvas.notifications")


class NotificationDispatcher:
    """
    Sends notifications to all configured providers simultaneously.
    
    Features:
        - Fan-out to Telegram, Discord, Email (all configured providers)
        - Per-notification database logging
        - Graceful failure (one provider failure doesn't stop others)
        - Type-safe event routing
    """

    def __init__(self, providers: Optional[List[BaseNotificationProvider]] = None) -> None:
        if providers is not None:
            self.providers = providers
        else:
            self.providers = self._load_configured_providers()

    def _load_configured_providers(self) -> List[BaseNotificationProvider]:
        """Instantiate and return the Telegram provider."""
        from app.services.notifications.telegram import TelegramProvider

        provider = TelegramProvider()
        if provider.is_configured():
            logger.info("Notification provider loaded: %s", provider.provider_name)
            return [provider]
        else:
            logger.warning("Telegram provider not fully configured — skipping.")
            return []

    def dispatch(
        self,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        title: Optional[str] = None,
        event_type: str = "generic",
        upload_id: Optional[int] = None,
        db_session=None,
    ) -> int:
        """
        Send a notification to all providers and log to database.

        Args:
            message: Notification message body.
            level: Severity level.
            title: Optional title.
            event_type: Event type string for logging (e.g., "upload_success").
            upload_id: Related upload ID (if applicable).
            db_session: Database session for logging (optional).

        Returns:
            Number of providers that successfully delivered the message.
        """
        success_count = 0

        for provider in self.providers:
            success = False
            error_msg = None

            try:
                success = provider.send(message, level=level, title=title)
                if success:
                    success_count += 1
            except Exception as e:
                error_msg = str(e)
                logger.error("Provider %s raised exception: %s", provider.provider_name, e)

            # Log to database
            if db_session:
                self._log_to_db(
                    db_session=db_session,
                    provider=provider.provider_name,
                    event_type=event_type,
                    message=message,
                    upload_id=upload_id,
                    success=success,
                    error=error_msg,
                )

        logger.info(
            "Notification dispatched: event=%s level=%s providers=%d/%d succeeded",
            event_type,
            level.value,
            success_count,
            len(self.providers),
        )

        return success_count

    def _log_to_db(
        self,
        db_session,
        provider: str,
        event_type: str,
        message: str,
        upload_id: Optional[int],
        success: bool,
        error: Optional[str],
    ) -> None:
        """Log a notification attempt to the database."""
        try:
            from app.models.notification_log import NotificationLog

            log = NotificationLog(
                provider=provider,
                event_type=event_type,
                upload_id=upload_id,
                message=message[:2000] if message else None,  # Truncate long messages
                success=success,
                error=error,
                sent_at=datetime.utcnow(),
            )
            db_session.add(log)
            db_session.commit()
        except Exception as e:
            logger.error("Failed to log notification to DB: %s", e)

    # ---------------------------------------------------------------------------
    # Convenience methods for common events
    # ---------------------------------------------------------------------------

    def notify_upload_started(self, filename: str, db_session=None) -> None:
        from app.config.constants import NOTIF_UPLOAD_STARTED
        from app.config.settings import settings

        msg = NOTIF_UPLOAD_STARTED.format(
            filename=filename,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        )
        self.dispatch(msg, NotificationLevel.INFO, "Upload Started", "upload_started", db_session=db_session)

    def notify_upload_success(
        self,
        filename: str,
        title: str,
        youtube_url: str,
        queue_remaining: int,
        days_remaining: int,
        upload_id: Optional[int] = None,
        db_session=None,
    ) -> None:
        from app.config.constants import NOTIF_UPLOAD_SUCCESS

        msg = NOTIF_UPLOAD_SUCCESS.format(
            filename=filename,
            title=title,
            youtube_url=youtube_url,
            queue_remaining=queue_remaining,
            days_remaining=days_remaining,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        )
        self.dispatch(msg, NotificationLevel.SUCCESS, "Upload Successful! 🎉", "upload_success", upload_id, db_session)

    def notify_upload_failed(
        self,
        filename: str,
        error: str,
        retry_count: int,
        next_retry_mins: int,
        upload_id: Optional[int] = None,
        db_session=None,
    ) -> None:
        from app.config.constants import NOTIF_UPLOAD_FAILED

        msg = NOTIF_UPLOAD_FAILED.format(
            filename=filename,
            error=error[:200],
            retry_count=retry_count,
            next_retry_mins=next_retry_mins,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        )
        self.dispatch(msg, NotificationLevel.ERROR, "Upload Failed", "upload_failed", upload_id, db_session)

    def notify_all_retries_failed(
        self, filename: str, error: str, upload_id: Optional[int] = None, db_session=None
    ) -> None:
        from app.config.constants import NOTIF_ALL_RETRIES_FAILED

        msg = NOTIF_ALL_RETRIES_FAILED.format(
            filename=filename,
            error=error[:200],
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        )
        self.dispatch(msg, NotificationLevel.CRITICAL, "All Retries Failed!", "all_retries_failed", upload_id, db_session)

    def notify_queue_empty(self, total_uploaded: int, db_session=None) -> None:
        from app.config.constants import NOTIF_QUEUE_EMPTY

        msg = NOTIF_QUEUE_EMPTY.format(
            brand_name=settings.brand_name,
            total_uploaded=total_uploaded,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        )
        self.dispatch(msg, NotificationLevel.SUCCESS, "Queue Empty 🎉", "queue_empty", db_session=db_session)

    def notify_health_check_failed(
        self, component: str, error: str, db_session=None
    ) -> None:
        from app.config.constants import NOTIF_HEALTH_CHECK_FAILED

        msg = NOTIF_HEALTH_CHECK_FAILED.format(
            component=component,
            error=error[:200],
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        )
        self.dispatch(msg, NotificationLevel.ERROR, "Health Check Alert!", "health_check_failed", db_session=db_session)

    def notify_scheduler_started(
        self,
        next_upload_time: str,
        queue_size: int,
        days_remaining: int,
        db_session=None,
    ) -> None:
        from app.config.constants import NOTIF_SCHEDULER_STARTED

        msg = NOTIF_SCHEDULER_STARTED.format(
            next_upload_time=next_upload_time,
            queue_size=queue_size,
            days_remaining=days_remaining,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        )
        self.dispatch(msg, NotificationLevel.INFO, "Scheduler Started 🟢", "scheduler_started", db_session=db_session)

    def notify_daily_summary(
        self,
        date: str,
        filename: str,
        title: str,
        youtube_status: str,
        queue_remaining: int,
        days_remaining: int,
        next_upload_time: str,
        total_uploaded: int,
        total_failed: int,
        db_session=None,
    ) -> None:
        from app.config.constants import NOTIF_DAILY_SUMMARY

        msg = NOTIF_DAILY_SUMMARY.format(
            date=date,
            filename=filename,
            title=title,
            youtube_status=youtube_status,
            queue_remaining=queue_remaining,
            days_remaining=days_remaining,
            next_upload_time=next_upload_time,
            total_uploaded=total_uploaded,
            total_failed=total_failed,
        )
        self.dispatch(msg, NotificationLevel.INFO, "📊 Daily Report", "daily_summary", db_session=db_session)
