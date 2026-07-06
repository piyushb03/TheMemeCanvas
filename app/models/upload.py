"""
TheMemeCanvas Automation Suite — Upload ORM Model
==================================================
Stores complete history of every video upload attempt,
including all metadata, platform IDs, and status.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)

from app.database.base import Base
from app.config.constants import UploadStage


class Upload(Base):
    """
    Represents one video upload record — from queue through completion.
    Each row corresponds to one video processed by the pipeline.
    """

    __tablename__ = "uploads"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # --- File Identity ---
    filename = Column(String(512), nullable=False, index=True)
    sha256 = Column(String(64), nullable=False, unique=True, index=True)
    drive_file_id = Column(String(256), nullable=True, unique=True, index=True)
    file_size_bytes = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # --- Generated Metadata ---
    title = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    caption = Column(Text, nullable=True)          # Instagram caption
    ai_opening = Column(String(512), nullable=True) # YouTube description opening
    tags_json = Column(Text, nullable=True)          # JSON list of YouTube tags
    hashtags_json = Column(Text, nullable=True)      # JSON list of Instagram hashtags

    # --- Platform Upload Results ---
    youtube_video_id = Column(String(64), nullable=True, unique=True, index=True)
    youtube_url = Column(String(512), nullable=True)
    youtube_status = Column(String(64), nullable=True)  # uploaded | failed | skipped

    instagram_reel_id = Column(String(64), nullable=True, unique=True, index=True)
    instagram_url = Column(String(512), nullable=True)
    instagram_status = Column(String(64), nullable=True)

    # --- Thumbnail ---
    thumbnail_path = Column(String(512), nullable=True)
    thumbnail_uploaded = Column(Boolean, default=False)

    # --- Pipeline Status ---
    status = Column(String(64), default=UploadStage.PENDING, index=True)
    current_stage = Column(String(64), nullable=True)

    # --- Retry Tracking ---
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    error_log_json = Column(Text, nullable=True)  # JSON list of all errors

    # --- Timestamps ---
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)

    # Drive folder tracking
    moved_to_uploaded = Column(Boolean, default=False)
    moved_to_failed = Column(Boolean, default=False)

    # --- Helpers ---

    @property
    def tags(self) -> List[str]:
        """Deserialize tags from JSON."""
        if self.tags_json:
            try:
                return json.loads(self.tags_json)
            except json.JSONDecodeError:
                return []
        return []

    @tags.setter
    def tags(self, value: List[str]) -> None:
        self.tags_json = json.dumps(value, ensure_ascii=False)

    @property
    def hashtags(self) -> List[str]:
        """Deserialize hashtags from JSON."""
        if self.hashtags_json:
            try:
                return json.loads(self.hashtags_json)
            except json.JSONDecodeError:
                return []
        return []

    @hashtags.setter
    def hashtags(self, value: List[str]) -> None:
        self.hashtags_json = json.dumps(value, ensure_ascii=False)

    @property
    def error_log(self) -> List[dict]:
        """Deserialize error log from JSON."""
        if self.error_log_json:
            try:
                return json.loads(self.error_log_json)
            except json.JSONDecodeError:
                return []
        return []

    def add_error(self, stage: str, error: str) -> None:
        """Append an error entry to the error log."""
        log = self.error_log
        log.append(
            {
                "stage": stage,
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        self.error_log_json = json.dumps(log, ensure_ascii=False)
        self.last_error = error

    def is_success(self) -> bool:
        return self.status == UploadStage.COMPLETED

    def is_failed(self) -> bool:
        return self.status == UploadStage.FAILED

    def __repr__(self) -> str:
        return f"<Upload id={self.id} filename={self.filename!r} status={self.status!r}>"
