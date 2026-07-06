"""
TheMemeCanvas Automation Suite — Logging Setup
===============================================
Configures rotating file handlers for each service/domain.
Call setup_logging() once at application startup.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from app.config.settings import settings

LOG_DIR = Path("logs")
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# One log file per service — keeps things clean and searchable
LOG_FILES = {
    "thememecanvas": "system.log",
    "thememecanvas.scheduler": "scheduler.log",
    "thememecanvas.drive": "drive.log",
    "thememecanvas.youtube": "youtube.log",
    "thememecanvas.ai": "ai.log",
    "thememecanvas.notifications": "notifications.log",
    "thememecanvas.pipeline": "pipeline.log",
    "thememecanvas.database": "database.log",
}

# Errors from any logger are also written to errors.log
ERROR_LOG_FILE = "errors.log"


def setup_logging() -> None:
    """
    Initialize all loggers with rotating file handlers + console handler.
    Call this exactly once at application startup.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # --- Root logger: console output ---
    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        root.addHandler(console_handler)

    # --- Error log: catches WARNING+ from all loggers ---
    error_handler = _rotating_handler(LOG_DIR / ERROR_LOG_FILE, formatter, level=logging.WARNING)

    # --- Per-service loggers ---
    for logger_name, log_filename in LOG_FILES.items():
        log = logging.getLogger(logger_name)
        log.setLevel(level)
        log.propagate = True  # Still goes to root/console

        file_handler = _rotating_handler(LOG_DIR / log_filename, formatter, level=level)

        # Avoid duplicate handlers if setup_logging() called again
        if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in log.handlers):
            log.addHandler(file_handler)
            log.addHandler(error_handler)

    logging.getLogger("thememecanvas").info(
        "Logging initialized. Log dir: %s | Level: %s", LOG_DIR.absolute(), settings.log_level
    )


def _rotating_handler(
    filepath: Path,
    formatter: logging.Formatter,
    level: int = logging.DEBUG,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 7,
) -> logging.handlers.RotatingFileHandler:
    """Create a rotating file handler."""
    handler = logging.handlers.RotatingFileHandler(
        filepath,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function — returns a named logger under the thememecanvas namespace.
    Usage: logger = get_logger("drive")  → thememecanvas.drive
    """
    return logging.getLogger(f"thememecanvas.{name}")
