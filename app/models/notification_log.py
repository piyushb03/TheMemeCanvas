"""
TheMemeCanvas Automation Suite — Notification Log ORM Model
===========================================================
Records every notification sent (or failed) for audit & debugging.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func

from app.database.base import Base


class NotificationLog(Base):
    """Records all outbound notification attempts."""

    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Which provider sent this?
    provider = Column(String(64), nullable=False, index=True)  # telegram | discord | email

    # Event type
    event_type = Column(String(128), nullable=False, index=True)  # upload_success | queue_empty | etc.

    # Linked upload (if applicable)
    upload_id = Column(Integer, nullable=True, index=True)

    # Message content
    message = Column(Text, nullable=True)

    # Delivery status
    success = Column(Boolean, default=False, index=True)
    error = Column(Text, nullable=True)

    # Timestamps
    sent_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<NotificationLog id={self.id} provider={self.provider!r} event={self.event_type!r} success={self.success}>"
