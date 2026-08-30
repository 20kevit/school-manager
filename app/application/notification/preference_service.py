"""Notification preference application service."""

from __future__ import annotations

from app.domain.notification import NotificationChannel, NotificationType
from app.extensions import db
from app.infrastructure.database.models import NotificationPreferenceModel


class PreferenceError(Exception):
    """Raised when a preference operation fails."""


def get_user_preferences(user_id: int) -> list[NotificationPreferenceModel]:
    """Get all notification preferences for a user."""
    return (
        NotificationPreferenceModel.query.filter_by(user_id=user_id)
        .order_by(
            NotificationPreferenceModel.notification_type,
            NotificationPreferenceModel.channel,
        )
        .all()
    )


def get_preference(
    user_id: int,
    notification_type: NotificationType,
    channel: NotificationChannel,
) -> NotificationPreferenceModel | None:
    """Get a specific preference."""
    return NotificationPreferenceModel.query.filter_by(
        user_id=user_id,
        notification_type=notification_type,
        channel=channel,
    ).first()


def update_preference(
    user_id: int,
    notification_type: NotificationType,
    channel: NotificationChannel,
    enabled: bool,
) -> NotificationPreferenceModel:
    """Update or create a notification preference."""
    pref = NotificationPreferenceModel.query.filter_by(
        user_id=user_id,
        notification_type=notification_type,
        channel=channel,
    ).first()

    if pref is None:
        pref = NotificationPreferenceModel(
            user_id=user_id,
            notification_type=notification_type,
            channel=channel,
            enabled=enabled,
        )
        db.session.add(pref)
    else:
        pref.enabled = enabled

    db.session.commit()
    return pref


def update_preferences_bulk(
    user_id: int,
    preferences: list[dict],
) -> list[NotificationPreferenceModel]:
    """Update multiple preferences at once.

    Each dict should have: notification_type, channel, enabled.
    """
    result = []
    for pref_data in preferences:
        pref = update_preference(
            user_id=user_id,
            notification_type=NotificationType(pref_data["notification_type"]),
            channel=NotificationChannel(pref_data["channel"]),
            enabled=pref_data["enabled"],
        )
        result.append(pref)
    return result


def is_channel_enabled(
    user_id: int,
    notification_type: NotificationType,
    channel: NotificationChannel,
) -> bool:
    """Check if a user has enabled a channel for a notification type."""
    from app.domain.notification import MANDATORY_NOTIFICATION_TYPES

    if notification_type in MANDATORY_NOTIFICATION_TYPES:
        return True

    pref = get_preference(user_id, notification_type, channel)
    if pref is None:
        return True  # Default: enabled
    return pref.enabled


def get_preference_matrix(user_id: int) -> dict[str, dict[str, bool]]:
    """Get a user's preferences as a matrix: {type: {channel: enabled}}."""
    prefs = get_user_preferences(user_id)
    matrix: dict[str, dict[str, bool]] = {}
    for pref in prefs:
        if pref.notification_type not in matrix:
            matrix[pref.notification_type] = {}
        matrix[pref.notification_type][pref.channel] = pref.enabled
    return matrix
