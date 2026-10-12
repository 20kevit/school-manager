"""SMS notification provider — generic abstraction."""

from __future__ import annotations

import os

from app.infrastructure.notification.providers import (
    NotificationProvider,
    ProviderResult,
)


class SmsProvider(NotificationProvider):
    """Generic SMS provider.

    Reads configuration from environment variables:
      SMS_PROVIDER (currently only 'generic' supported)
      SMS_API_KEY
      SMS_SENDER
      SMS_API_URL
    """

    def __init__(self) -> None:
        self._api_key = os.getenv("SMS_API_KEY", "")
        self._sender = os.getenv("SMS_SENDER", "")
        self._api_url = os.getenv("SMS_API_URL", "")

    @property
    def name(self) -> str:
        return "generic_sms"

    @property
    def channel(self) -> str:
        return "SMS"

    def is_available(self) -> bool:
        return bool(self._api_key and self._sender and self._api_url)

    def validate_recipient(self, recipient: str) -> bool:
        """Validate Iranian mobile number format."""
        digits = recipient.strip().replace("+98", "0").replace("98", "0")
        return digits.startswith("09") and len(digits) == 11 and digits.isdigit()

    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
    ) -> ProviderResult:
        if not self.is_available():
            return ProviderResult(
                success=False,
                error="SMS provider not configured.",
                provider_name=self.name,
            )

        if not self.validate_recipient(recipient):
            return ProviderResult(
                success=False,
                error=f"Invalid SMS recipient: {recipient}",
                provider_name=self.name,
            )

        try:
            return self._send_via_api(recipient, body)
        except Exception as exc:
            return ProviderResult(
                success=False,
                error=f"SMS send failed: {exc}",
                provider_name=self.name,
            )

    def _send_via_api(self, recipient: str, body: str) -> ProviderResult:
        """Send SMS via configured API.

        No generic HTTP delivery is implemented: provider request formats
        differ per vendor and must not be fabricated. Callers must treat
        SMS as unavailable until a real provider integration lands, instead
        of recording a delivery that never happened.
        """
        import logging

        logging.getLogger(__name__).warning(
            "SMS delivery requested for %s but no provider HTTP integration "
            "exists; reporting failure instead of a false success.",
            self.name,
        )
        return ProviderResult(
            success=False,
            error="SMS provider HTTP delivery is not implemented.",
            provider_name=self.name,
        )
