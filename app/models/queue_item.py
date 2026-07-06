"""
TheMemeCanvas Automation Suite — Queue Item ORM Model
=====================================================
Tracks every video discovered in the Google Drive queue folder.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.database.base import Base


class QueueItem(Base):
    """
    Represents a video discovered in the Google Drive queue folder.
    Separate from Upload so we can track queue state independently.
    """

    __tablename__ = "queue_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Drive file info
    drive_file_id = Column(String(256), nullable=False, unique=True, index=True)
    filename = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    drive_created_time = Column(DateTime, nullable=True)
    drive_modified_time = Column(DateTime, nullable=True)
    mime_type = Column(String(128), nullable=True)

    # Has a matching thumbnail in Drive?
    has_thumbnail = Column(Boolean, default=False)
    thumbnail_drive_file_id = Column(String(256), nullable=True)

    # Queue management
    is_processed = Column(Boolean, default=False, index=True)
    is_skipped = Column(Boolean, default=False, index=True)
    priority = Column(Integer, default=0)  # Higher = processed sooner

    # Linked upload (once processed)
    upload_id = Column(Integer, nullable=True)

    # Timestamps
    discovered_at = Column(DateTime, server_default=func.now(), nullable=False)
    scheduled_for = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<QueueItem id={self.id} filename={self.filename!r} processed={self.is_processed}>"
