"""Telegram Bot API notification provider."""

from __future__ import annotations

import os

from app.infrastructure.notification.providers import (
    NotificationProvider,
    ProviderResult,
)


class TelegramProvider(NotificationProvider):
    """Telegram Bot API provider.

    Reads configuration from environment variables:
      TELEGRAM_BOT_TOKEN
    """

    def __init__(self) -> None:
        self._bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    @property
    def name(self) -> str:
        return "telegram"

    @property
    def channel(self) -> str:
        return "TELEGRAM"

    def is_available(self) -> bool:
        return bool(self._bot_token)

    def validate_recipient(self, recipient: str) -> bool:
        """Recipient should be a Telegram chat ID (numeric or @username)."""
        recipient = recipient.strip()
        if not recipient:
            return False
        if recipient.startswith("@"):
            return len(recipient) > 1
        return recipient.lstrip("-").isdigit()

    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
    ) -> ProviderResult:
        if not self.is_available():
            return ProviderResult(
                success=False,
                error="Telegram bot token not configured.",
                provider_name=self.name,
            )

        if not self.validate_recipient(recipient):
            return ProviderResult(
                success=False,
                error=f"Invalid Telegram recipient: {recipient}",
                provider_name=self.name,
            )

        try:
            return self._send_via_api(recipient, subject, body)
        except Exception as exc:
            return ProviderResult(
                success=False,
                error=f"Telegram send failed: {exc}",
                provider_name=self.name,
            )

    def _send_via_api(self, recipient: str, subject: str, body: str) -> ProviderResult:
        """Send message via Telegram Bot API.

        Placeholder for actual HTTP integration.
        """
        return ProviderResult(
            success=True,
            provider_message_id="",
            provider_name=self.name,
        )
