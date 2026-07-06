"""
TheMemeCanvas Automation Suite — Health Check System
=====================================================
Runs comprehensive checks against all integrated services.
Called daily by the scheduler and available via the dashboard API.
"""

from __future__ import annotations

import logging
import shutil
import socket
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("thememecanvas.pipeline")


@dataclass
class HealthResult:
    """Result of a single health check."""

    component: str
    status: str  # "ok" | "warning" | "error"
    message: str
    latency_ms: Optional[float] = None
    checked_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_healthy(self) -> bool:
        return self.status == "ok"


@dataclass
class HealthReport:
    """Aggregated health report for all components."""

    results: List[HealthResult] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def overall_status(self) -> str:
        statuses = {r.status for r in self.results}
        if "error" in statuses:
            return "error"
        if "warning" in statuses:
            return "warning"
        return "ok"

    @property
    def is_healthy(self) -> bool:
        return self.overall_status == "ok"

    def to_dict(self) -> Dict:
        return {
            "overall_status": self.overall_status,
            "checked_at": self.checked_at.isoformat(),
            "components": [
                {
                    "component": r.component,
                    "status": r.status,
                    "message": r.message,
                    "latency_ms": r.latency_ms,
                    "checked_at": r.checked_at.isoformat(),
                }
                for r in self.results
            ],
        }


def check_internet() -> HealthResult:
    """Verify internet connectivity by connecting to Google DNS."""
    import time

    start = time.monotonic()
    try:
        socket.setdefaulttimeout(5)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        latency = (time.monotonic() - start) * 1000
        return HealthResult("internet", "ok", "Connected", latency_ms=latency)
    except Exception as e:
        return HealthResult("internet", "error", f"No internet: {e}")


def check_disk_space() -> HealthResult:
    """Check available disk space."""
    from app.config.settings import settings

    try:
        usage = shutil.disk_usage(".")
        used_pct = (usage.used / usage.total) * 100
        free_gb = usage.free / (1024**3)

        if used_pct >= settings.disk_warning_threshold_percent:
            return HealthResult(
                "disk",
                "warning",
                f"Disk {used_pct:.1f}% used ({free_gb:.1f} GB free)",
            )
        return HealthResult(
            "disk",
            "ok",
            f"Disk {used_pct:.1f}% used ({free_gb:.1f} GB free)",
        )
    except Exception as e:
        return HealthResult("disk", "error", f"Cannot check disk: {e}")


def check_database() -> HealthResult:
    """Verify database connection and schema."""
    import time

    start = time.monotonic()
    try:
        from app.database.base import SessionLocal
        from app.models.upload import Upload

        db = SessionLocal()
        count = db.query(Upload).count()
        db.close()
        latency = (time.monotonic() - start) * 1000
        return HealthResult("database", "ok", f"Connected. {count} upload records.", latency_ms=latency)
    except Exception as e:
        return HealthResult("database", "error", f"Database error: {e}")


def check_google_drive() -> HealthResult:
    """Verify Google Drive API connectivity."""
    import time

    start = time.monotonic()
    try:
        from app.services.drive.client import DriveClient

        client = DriveClient()
        about = client.service.about().get(fields="user").execute()
        latency = (time.monotonic() - start) * 1000
        email = about.get("user", {}).get("emailAddress", "unknown")
        return HealthResult("google_drive", "ok", f"Connected as {email}", latency_ms=latency)
    except Exception as e:
        return HealthResult("google_drive", "error", f"Drive error: {e}")


def check_youtube() -> HealthResult:
    """Verify YouTube API access."""
    import time

    start = time.monotonic()
    try:
        from app.services.youtube.client import YouTubeClient

        client = YouTubeClient()
        result = client.service.channels().list(part="snippet", mine=True).execute()
        latency = (time.monotonic() - start) * 1000
        items = result.get("items", [])
        channel = items[0]["snippet"]["title"] if items else "unknown"
        return HealthResult("youtube", "ok", f"Channel: {channel}", latency_ms=latency)
    except Exception as e:
        return HealthResult("youtube", "error", f"YouTube error: {e}")





def check_ai_provider() -> HealthResult:
    """Verify AI provider API key validity."""
    import time
    from app.config.settings import settings

    start = time.monotonic()
    try:
        import openai
        client = openai.OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.groq_api_key,
        )
        client.models.list()
        latency = (time.monotonic() - start) * 1000
        return HealthResult("ai_provider", "ok", "Groq API connected.", latency_ms=latency)
    except Exception as e:
        return HealthResult("ai_provider", "error", f"AI provider error: {e}")


def check_notifications() -> HealthResult:
    """Verify Telegram notification provider is configured."""
    from app.config.settings import settings

    if settings.telegram_bot_token != "YOUR_TELEGRAM_BOT_TOKEN" and settings.telegram_chat_id != "YOUR_TELEGRAM_CHAT_ID":
        return HealthResult("notifications", "ok", "Telegram Bot configured.")
    else:
        return HealthResult("notifications", "warning", "Telegram credentials missing or at default values.")


def run_full_health_check() -> HealthReport:
    """
    Run all health checks and return a consolidated report.
    Called daily by the scheduler and on-demand from the dashboard.
    """
    logger.info("Running full health check...")

    checkers = [
        check_internet,
        check_disk_space,
        check_database,
        check_google_drive,
        check_youtube,
        check_ai_provider,
        check_notifications,
    ]

    report = HealthReport()

    for checker in checkers:
        try:
            result = checker()
        except Exception as exc:
            logger.exception("Health check crashed for checker: %s", checker.__name__)
            result = HealthResult(
                checker.__name__.replace("check_", ""),
                "error",
                f"Health check crashed: {exc}",
            )

        report.results.append(result)
        emoji = "✅" if result.is_healthy else ("⚠️" if result.status == "warning" else "❌")
        logger.info("%s %s: %s", emoji, result.component, result.message)

    logger.info(
        "Health check complete. Overall: %s (%d/%d healthy)",
        report.overall_status,
        sum(1 for r in report.results if r.is_healthy),
        len(report.results),
    )

    return report


if __name__ == "__main__":
    from app.utils.logging_setup import setup_logging
    from app.database.base import init_db
    setup_logging()
    init_db()
    run_full_health_check()
