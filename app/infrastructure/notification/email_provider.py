"""Email (SMTP) notification provider."""

from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText

from app.infrastructure.notification.providers import (
    NotificationProvider,
    ProviderResult,
)


class EmailProvider(NotificationProvider):
    """SMTP email provider.

    Reads configuration from environment variables:
      MAIL_SERVER
      MAIL_PORT
      MAIL_USERNAME
      MAIL_PASSWORD
      MAIL_USE_TLS
      MAIL_USE_SSL
      MAIL_DEFAULT_SENDER
    """

    def __init__(self) -> None:
        self._server = os.getenv("MAIL_SERVER", "")
        self._port = int(os.getenv("MAIL_PORT", "587"))
        self._username = os.getenv("MAIL_USERNAME", "")
        self._password = os.getenv("MAIL_PASSWORD", "")
        self._use_tls = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
        self._use_ssl = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
        self._default_sender = os.getenv("MAIL_DEFAULT_SENDER", self._username)

    @property
    def name(self) -> str:
        return "smtp_email"

    @property
    def channel(self) -> str:
        return "EMAIL"

    def is_available(self) -> bool:
        return bool(self._server and self._username and self._password)

    def validate_recipient(self, recipient: str) -> bool:
        """Basic email format validation."""
        recipient = recipient.strip()
        return "@" in recipient and "." in recipient.split("@")[-1]

    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
    ) -> ProviderResult:
        if not self.is_available():
            return ProviderResult(
                success=False,
                error="Email provider not configured.",
                provider_name=self.name,
            )

        if not self.validate_recipient(recipient):
            return ProviderResult(
                success=False,
                error=f"Invalid email recipient: {recipient}",
                provider_name=self.name,
            )

        try:
            return self._send_via_smtp(recipient, subject, body)
        except Exception as exc:
            return ProviderResult(
                success=False,
                error=f"Email send failed: {exc}",
                provider_name=self.name,
            )

    def _send_via_smtp(self, recipient: str, subject: str, body: str) -> ProviderResult:
        """Send email via SMTP."""
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self._default_sender
        msg["To"] = recipient

        if self._use_ssl:
            server = smtplib.SMTP_SSL(self._server, self._port, timeout=30)
        else:
            server = smtplib.SMTP(self._server, self._port, timeout=30)
            if self._use_tls:
                server.starttls()

        try:
            server.login(self._username, self._password)
            server.sendmail(self._default_sender, [recipient], msg.as_string())
        finally:
            server.quit()

        return ProviderResult(
            success=True,
            provider_message_id="",
            provider_name=self.name,
        )
