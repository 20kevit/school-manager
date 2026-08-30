"""Provider abstraction for notification delivery."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderResult:
    """Normalized result from a notification provider."""

    success: bool
    provider_message_id: str = ""
    error: str = ""
    provider_name: str = ""


class NotificationProvider(ABC):
    """Abstract base for notification channel providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider name (e.g. 'kavenegar_sms')."""

    @property
    @abstractmethod
    def channel(self) -> str:
        """Channel this provider delivers (e.g. 'SMS')."""

    @abstractmethod
    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
    ) -> ProviderResult:
        """Send a notification to the given recipient."""

    @abstractmethod
    def validate_recipient(self, recipient: str) -> bool:
        """Check if the recipient address is valid for this provider."""

    def is_available(self) -> bool:
        """Whether the provider is configured and ready."""
        return True


@dataclass
class ProviderHealth:
    """Health status for a provider."""

    name: str
    channel: str
    available: bool
    message: str = ""


class NullProvider(NotificationProvider):
    """Fallback provider when no real provider is configured."""

    @property
    def name(self) -> str:
        return "null"

    @property
    def channel(self) -> str:
        return "NULL"

    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
    ) -> ProviderResult:
        return ProviderResult(
            success=False,
            error="No provider configured for this channel.",
            provider_name=self.name,
        )

    def validate_recipient(self, recipient: str) -> bool:
        return False

    def is_available(self) -> bool:
        return False
