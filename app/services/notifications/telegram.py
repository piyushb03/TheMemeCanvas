"""
TheMemeCanvas Automation Suite — Telegram Bot Notification Provider
==================================================================
Sends notifications via Telegram Bot API using python-telegram-bot.
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

from app.config.settings import settings
from app.services.notifications.base import BaseNotificationProvider, NotificationLevel

logger = logging.getLogger("thememecanvas.notifications")

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

# Emoji prefixes by level
LEVEL_EMOJI = {
    NotificationLevel.INFO: "ℹ️",
    NotificationLevel.SUCCESS: "✅",
    NotificationLevel.WARNING: "⚠️",
    NotificationLevel.ERROR: "❌",
    NotificationLevel.CRITICAL: "🚨",
}


class TelegramProvider(BaseNotificationProvider):
    """
    Sends Markdown-formatted messages via Telegram Bot API.

    Setup:
        1. Create a bot via @BotFather on Telegram
        2. Get your Chat ID via @userinfobot
        3. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env
    """

    def __init__(self) -> None:
        self.token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.error_chat_id = settings.telegram_error_chat_id or settings.telegram_chat_id

    @property
    def provider_name(self) -> str:
        return "Telegram"

    def is_configured(self) -> bool:
        return (
            bool(self.token)
            and self.token != "YOUR_TELEGRAM_BOT_TOKEN"
            and bool(self.chat_id)
            and self.chat_id != "YOUR_TELEGRAM_CHAT_ID"
        )

    def send(
        self,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        title: Optional[str] = None,
    ) -> bool:
        """Send a message via Telegram Bot API."""
        if not self.is_configured():
            logger.warning("Telegram not configured. Skipping notification.")
            return False

        # Route errors to error chat
        chat_id = self.error_chat_id if level in (NotificationLevel.ERROR, NotificationLevel.CRITICAL) else self.chat_id

        # Build message with emoji prefix
        emoji = LEVEL_EMOJI.get(level, "")
        full_message = message

        if title:
            full_message = f"{emoji} *{title}*\n\n{message}"

        try:
            url = TELEGRAM_API.format(token=self.token, method="sendMessage")
            payload = {
                "chat_id": chat_id,
                "text": full_message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }

            response = requests.post(url, json=payload, timeout=15)

            if response.ok:
                logger.debug("Telegram notification sent successfully.")
                return True
            else:
                logger.error(
                    "Telegram API error: %s %s",
                    response.status_code,
                    response.text[:200],
                )
                return False

        except requests.RequestException as e:
            logger.error("Telegram send failed: %s", e)
            return False

    def send_photo(
        self,
        photo_path: str,
        caption: Optional[str] = None,
    ) -> bool:
        """Send a photo (e.g., thumbnail) via Telegram."""
        if not self.is_configured():
            return False

        try:
            url = TELEGRAM_API.format(token=self.token, method="sendPhoto")
            with open(photo_path, "rb") as photo:
                response = requests.post(
                    url,
                    data={"chat_id": self.chat_id, "caption": caption or "", "parse_mode": "Markdown"},
                    files={"photo": photo},
                    timeout=30,
                )

            return response.ok
        except Exception as e:
            logger.error("Telegram photo send failed: %s", e)
            return False
