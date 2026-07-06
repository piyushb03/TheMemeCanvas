"""
TheMemeCanvas Automation Suite — Abstract Notification Provider
===============================================================
All notification providers implement this interface.
Adding a new provider (WhatsApp, Slack, etc.) requires zero changes
to the calling dispatcher code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional


class NotificationLevel(str, Enum):
    """Notification severity levels."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class BaseNotificationProvider(ABC):
    """
    Abstract base class for all notification providers.

    Implementations:
        - TelegramProvider (priority 1)
        - DiscordProvider (priority 2)
        - EmailProvider (priority 3)
        - WhatsAppProvider (future)
        - SlackProvider (future)
    """

    @abstractmethod
    def send(
        self,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        title: Optional[str] = None,
    ) -> bool:
        """
        Send a notification message.

        Args:
            message: The notification body text (supports Markdown).
            level: Severity level (affects formatting/color).
            title: Optional title/subject for the message.

        Returns:
            True if sent successfully, False otherwise.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return a human-readable provider name."""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if this provider has valid credentials."""
        ...
