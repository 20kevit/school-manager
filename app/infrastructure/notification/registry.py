"""Provider registry — resolves channel to provider instance."""

from __future__ import annotations

import logging

from app.infrastructure.notification.providers import NotificationProvider, NullProvider

logger = logging.getLogger(__name__)

_registry: dict[str, NotificationProvider] = {}


def register_provider(provider: NotificationProvider) -> None:
    """Register a provider instance."""
    _registry[provider.channel] = provider
    logger.info(
        "Registered provider %s for channel %s", provider.name, provider.channel
    )


def get_provider(channel: str) -> NotificationProvider:
    """Get the provider for a channel, or a NullProvider if none registered."""
    provider = _registry.get(channel)
    if provider is None:
        return NullProvider()
    return provider


def get_all_providers() -> list[NotificationProvider]:
    """Return all registered providers."""
    return list(_registry.values())


def get_provider_health() -> list[dict]:
    """Return health status of all registered providers."""
    result = []
    for provider in _registry.values():
        result.append(
            {
                "name": provider.name,
                "channel": provider.channel,
                "available": provider.is_available(),
            }
        )
    return result


def init_default_providers() -> None:
    """Initialize and register default notification providers."""
    from app.infrastructure.notification.bale_provider import BaleProvider
    from app.infrastructure.notification.email_provider import EmailProvider
    from app.infrastructure.notification.sms_provider import SmsProvider
    from app.infrastructure.notification.telegram_provider import TelegramProvider

    providers = [SmsProvider(), TelegramProvider(), BaleProvider(), EmailProvider()]
    for provider in providers:
        register_provider(provider)
