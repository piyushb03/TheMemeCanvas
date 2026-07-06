"""
TheMemeCanvas Automation Suite — Application Settings
======================================================
Pydantic BaseSettings reads from environment variables / .env file.
All configuration is centralized here — no scattered os.getenv() calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Core application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    app_secret_key: str = "change-me-in-production"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # Scheduler
    upload_time: str = "21:00"  # HH:MM 24h
    timezone: str = "Asia/Kolkata"
    upload_order: str = "oldest_first"  # oldest_first | newest_first | random
    uploads_paused: bool = False

    # Google Drive
    google_service_account_file: Optional[Path] = None
    google_service_account_json: Optional[str] = None
    google_oauth_client_secrets_file: Optional[Path] = None
    google_oauth_token_file: Optional[Path] = None
    drive_queue_folder_id: str = "YOUR_GOOGLE_DRIVE_QUEUE_FOLDER_ID"
    drive_uploaded_folder_id: str = "YOUR_GOOGLE_DRIVE_UPLOADED_FOLDER_ID"
    drive_failed_folder_id: str = "YOUR_GOOGLE_DRIVE_FAILED_FOLDER_ID"

    # YouTube
    youtube_oauth_client_secrets_file: Optional[Path] = None
    youtube_oauth_client_secrets_json: Optional[str] = None
    youtube_oauth_token_file: Optional[Path] = None
    youtube_oauth_token_json: Optional[str] = None
    youtube_channel_id: str = "YOUR_YOUTUBE_CHANNEL_ID"
    youtube_privacy_status: str = "public"
    youtube_category_id: int = 24
    youtube_made_for_kids: bool = False
    youtube_max_tags: int = 30


    # AI
    ai_provider: str = "groq"
    groq_api_key: Optional[str] = None
    groq_model: str = "llama3-70b-8192"

    # Notifications
    telegram_bot_token: str = "YOUR_TELEGRAM_BOT_TOKEN"
    telegram_chat_id: str = "YOUR_TELEGRAM_CHAT_ID"
    telegram_error_chat_id: Optional[str] = None

    # Database
    database_url: str = "sqlite:///./data/thememecanvas.db"

    # Retry
    retry_delays_minutes: str = "5,15,30,60"
    max_retry_attempts: int = 4

    # Thumbnail
    auto_generate_thumbnail: bool = True
    default_thumbnail_path: Path = Path("assets/default_thumbnail.jpg")

    # Storage
    temp_download_dir: Path = Path("temp_downloads")
    max_temp_disk_mb: int = 2048

    # Health check
    health_check_time: str = "08:00"
    disk_warning_threshold_percent: int = 85

    # Brand
    brand_name: str = "TheMemeCanvas"
    youtube_channel_url: str = "https://www.youtube.com/@TheMemeCanvas"

    @field_validator("upload_order")
    @classmethod
    def validate_upload_order(cls, v: str) -> str:
        allowed = {"oldest_first", "newest_first", "random"}
        if v not in allowed:
            raise ValueError(f"upload_order must be one of {allowed}")
        return v

    @field_validator("youtube_privacy_status")
    @classmethod
    def validate_privacy(cls, v: str) -> str:
        allowed = {"public", "private", "unlisted"}
        if v not in allowed:
            raise ValueError(f"youtube_privacy_status must be one of {allowed}")
        return v

    @property
    def retry_delays(self) -> List[int]:
        """Return list of retry delay minutes."""
        return [int(d.strip()) for d in self.retry_delays_minutes.split(",") if d.strip()]


# Singleton instance — import this everywhere
settings = AppSettings()
