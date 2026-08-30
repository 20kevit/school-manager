"""Bale Bot API notification provider."""

from __future__ import annotations

import os

from app.infrastructure.notification.providers import (
    NotificationProvider,
    ProviderResult,
)


class BaleProvider(NotificationProvider):
    """Bale Messenger Bot API provider.

    Reads configuration from environment variables:
      BALE_BOT_TOKEN
    """

    def __init__(self) -> None:
        self._bot_token = os.getenv("BALE_BOT_TOKEN", "")

    @property
    def name(self) -> str:
        return "bale"

    @property
    def channel(self) -> str:
        return "BALE"

    def is_available(self) -> bool:
        return bool(self._bot_token)

    def validate_recipient(self, recipient: str) -> bool:
        """Recipient should be a Bale chat ID."""
        recipient = recipient.strip()
        if not recipient:
            return False
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
                error="Bale bot token not configured.",
                provider_name=self.name,
            )

        if not self.validate_recipient(recipient):
            return ProviderResult(
                success=False,
                error=f"Invalid Bale recipient: {recipient}",
                provider_name=self.name,
            )

        try:
            return self._send_via_api(recipient, subject, body)
        except Exception as exc:
            return ProviderResult(
                success=False,
                error=f"Bale send failed: {exc}",
                provider_name=self.name,
            )

    def _send_via_api(self, recipient: str, subject: str, body: str) -> ProviderResult:
        """Send message via Bale Bot API.

        Placeholder for actual HTTP integration.
        """
        return ProviderResult(
            success=True,
            provider_message_id="",
            provider_name=self.name,
        )
