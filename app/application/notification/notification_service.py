"""Core notification application service."""

from __future__ import annotations

import logging
from datetime import datetime

from app.domain.notification import (
    MANDATORY_NOTIFICATION_TYPES,
    DeliveryStatus,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from app.extensions import db
from app.infrastructure.database.models import (
    InAppNotificationModel,
    NotificationDeliveryModel,
    NotificationModel,
    NotificationPreferenceModel,
    UserModel,
)
from app.infrastructure.notification.registry import get_provider

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    """Raised when a notification operation fails."""


def create_notification(
    notification_type: NotificationType,
    title: str,
    message: str,
    recipient_user_id: int,
    channels: list[NotificationChannel] | None = None,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    template_id: int | None = None,
    event_key: str | None = None,
    scheduled_at: datetime | None = None,
) -> NotificationModel:
    """Create a notification and its delivery records.

    Returns the created NotificationModel.
    """
    if channels is None:
        channels = [NotificationChannel.IN_APP]

    notification = NotificationModel(
        notification_type=notification_type,
        title=title,
        message=message,
        recipient_user_id=recipient_user_id,
        priority=priority,
        template_id=template_id,
        event_key=event_key,
        status=NotificationStatus.PENDING,
        scheduled_at=scheduled_at,
    )
    db.session.add(notification)
    db.session.flush()

    for channel in channels:
        delivery = NotificationDeliveryModel(
            notification_id=notification.id,
            channel=channel,
            status=DeliveryStatus.PENDING,
        )
        db.session.add(delivery)

    db.session.commit()
    return notification


def send_notification(notification_id: int) -> NotificationModel:
    """Send a notification through all its pending delivery channels.

    Respects user preferences (unless mandatory).
    Creates in-app notification for IN_APP channel.
    """
    notification = NotificationModel.query.get(notification_id)
    if notification is None:
        raise NotificationError("Notification not found.")

    if notification.status in (NotificationStatus.SENT, NotificationStatus.CANCELLED):
        return notification

    notification.status = NotificationStatus.SENDING
    db.session.commit()

    deliveries = NotificationDeliveryModel.query.filter_by(
        notification_id=notification_id
    ).all()

    any_success = False
    any_failed = False

    for delivery in deliveries:
        if delivery.status == DeliveryStatus.SENT:
            any_success = True
            continue

        channel = delivery.channel

        if channel == NotificationChannel.IN_APP:
            _send_in_app(notification, delivery)
            any_success = True
            continue

        if not _is_channel_enabled(
            notification.recipient_user_id,
            notification.notification_type,
            channel,
        ):
            delivery.status = DeliveryStatus.FAILED
            delivery.failure_reason = "Channel disabled by user preference."
            delivery.updated_at = datetime.now()
            any_failed = True
            continue

        provider = get_provider(channel)
        if not provider.is_available():
            delivery.status = DeliveryStatus.FAILED
            delivery.failure_reason = f"Provider for {channel} not available."
            delivery.updated_at = datetime.now()
            any_failed = True
            continue

        recipient = _get_recipient_address(notification.recipient_user_id, channel)
        if not recipient:
            delivery.status = DeliveryStatus.FAILED
            delivery.failure_reason = f"No contact info for {channel}."
            delivery.updated_at = datetime.now()
            any_failed = True
            continue

        delivery.attempt_count += 1
        delivery.provider_name = provider.name
        delivery.status = DeliveryStatus.SENT
        delivery.updated_at = datetime.now()

        result = provider.send(recipient, notification.title, notification.message)
        if result.success:
            delivery.status = DeliveryStatus.SENT
            delivery.provider_message_id = result.provider_message_id
            delivery.sent_at = datetime.now()
            any_success = True
        else:
            delivery.status = DeliveryStatus.FAILED
            delivery.failure_reason = result.error
            delivery.failed_at = datetime.now()
            any_failed = True

    if any_success and not any_failed:
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now()
    elif any_success and any_failed:
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now()
    elif any_failed:
        notification.status = NotificationStatus.FAILED
        notification.failed_at = datetime.now()
        notification.failure_reason = "All delivery channels failed."

    notification.updated_at = datetime.now()
    db.session.commit()
    return notification


def send_multi_channel_notification(
    notification_type: NotificationType,
    title: str,
    message: str,
    recipient_user_id: int,
    channels: list[NotificationChannel],
    priority: NotificationPriority = NotificationPriority.NORMAL,
    template_id: int | None = None,
    event_key: str | None = None,
) -> NotificationModel:
    """Create and send a notification across multiple channels."""
    notification = create_notification(
        notification_type=notification_type,
        title=title,
        message=message,
        recipient_user_id=recipient_user_id,
        channels=channels,
        priority=priority,
        template_id=template_id,
        event_key=event_key,
    )
    return send_notification(notification.id)


def cancel_notification(notification_id: int) -> NotificationModel:
    """Cancel a pending notification."""
    notification = NotificationModel.query.get(notification_id)
    if notification is None:
        raise NotificationError("Notification not found.")

    if notification.status == NotificationStatus.SENT:
        raise NotificationError("Cannot cancel a sent notification.")

    notification.status = NotificationStatus.CANCELLED
    notification.updated_at = datetime.now()

    deliveries = NotificationDeliveryModel.query.filter_by(
        notification_id=notification_id
    ).all()
    for delivery in deliveries:
        if delivery.status == DeliveryStatus.PENDING:
            delivery.status = DeliveryStatus.FAILED
            delivery.failure_reason = "Cancelled."
            delivery.updated_at = datetime.now()

    db.session.commit()
    return notification


def retry_notification(notification_id: int) -> NotificationModel:
    """Retry failed delivery for a notification."""
    notification = NotificationModel.query.get(notification_id)
    if notification is None:
        raise NotificationError("Notification not found.")

    if notification.status != NotificationStatus.FAILED:
        raise NotificationError("Only failed notifications can be retried.")

    notification.status = NotificationStatus.PENDING
    notification.retry_count += 1
    notification.failure_reason = ""
    notification.failed_at = None
    notification.updated_at = datetime.now()

    deliveries = NotificationDeliveryModel.query.filter_by(
        notification_id=notification_id
    ).all()
    for delivery in deliveries:
        if delivery.status == DeliveryStatus.FAILED:
            delivery.status = DeliveryStatus.PENDING
            delivery.failure_reason = ""
            delivery.failed_at = None
            delivery.updated_at = datetime.now()

    db.session.commit()
    return send_notification(notification_id)


def get_notification(notification_id: int) -> NotificationModel | None:
    """Get a notification by ID."""
    return NotificationModel.query.get(notification_id)


def list_notifications(
    recipient_user_id: int | None = None,
    status: str | None = None,
    notification_type: str | None = None,
    channel: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[NotificationModel]:
    """List notifications with optional filters."""
    query = NotificationModel.query

    if recipient_user_id is not None:
        query = query.filter_by(recipient_user_id=recipient_user_id)
    if status:
        query = query.filter_by(status=status)
    if notification_type:
        query = query.filter_by(notification_type=notification_type)

    query = query.order_by(NotificationModel.created_at.desc())
    query = query.offset(offset).limit(limit)

    return query.all()


def count_notifications(
    recipient_user_id: int | None = None,
    status: str | None = None,
) -> int:
    """Count notifications with optional filters."""
    query = NotificationModel.query

    if recipient_user_id is not None:
        query = query.filter_by(recipient_user_id=recipient_user_id)
    if status:
        query = query.filter_by(status=status)

    return query.count()


def send_manual_notification(
    recipient_user_ids: list[int],
    channel: NotificationChannel,
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.IN_APP_MESSAGE,
) -> list[NotificationModel]:
    """Send a manual notification to one or more recipients."""
    notifications = []
    for user_id in recipient_user_ids:
        try:
            n = create_notification(
                notification_type=notification_type,
                title=title,
                message=message,
                recipient_user_id=user_id,
                channels=[channel],
            )
            send_notification(n.id)
            notifications.append(n)
        except NotificationError:
            logger.exception("Failed to send manual notification to user %s", user_id)
    return notifications


def send_announcement(
    title: str,
    message: str,
    channels: list[NotificationChannel],
    recipient_user_ids: list[int],
    notification_type: NotificationType = NotificationType.ANNOUNCEMENT,
    priority: NotificationPriority = NotificationPriority.NORMAL,
) -> list[NotificationModel]:
    """Send an announcement to multiple users."""
    notifications = []
    for user_id in recipient_user_ids:
        try:
            n = create_notification(
                notification_type=notification_type,
                title=title,
                message=message,
                recipient_user_id=user_id,
                channels=channels,
                priority=priority,
            )
            send_notification(n.id)
            notifications.append(n)
        except NotificationError:
            logger.exception("Failed to send announcement to user %s", user_id)
    return notifications


def get_notification_deliveries(
    notification_id: int,
) -> list[NotificationDeliveryModel]:
    """Get delivery records for a notification."""
    return NotificationDeliveryModel.query.filter_by(
        notification_id=notification_id
    ).all()


def get_failed_notifications(limit: int = 50) -> list[NotificationModel]:
    """Get all failed notifications."""
    return (
        NotificationModel.query.filter_by(status=NotificationStatus.FAILED)
        .order_by(NotificationModel.created_at.desc())
        .limit(limit)
        .all()
    )


# ---------------------------------------------------------------------------
# In-App notifications
# ---------------------------------------------------------------------------


def create_in_app_notification(
    user_id: int,
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.IN_APP_MESSAGE,
    link: str = "",
    notification_id: int | None = None,
) -> InAppNotificationModel:
    """Create an in-app notification."""
    in_app = InAppNotificationModel(
        user_id=user_id,
        notification_id=notification_id,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
        read_status="UNREAD",
    )
    db.session.add(in_app)
    db.session.commit()
    return in_app


def get_user_in_app_notifications(
    user_id: int,
    unread_only: bool = False,
    limit: int = 50,
) -> list[InAppNotificationModel]:
    """Get in-app notifications for a user."""
    query = InAppNotificationModel.query.filter_by(user_id=user_id)
    if unread_only:
        query = query.filter_by(read_status="UNREAD")
    return query.order_by(InAppNotificationModel.created_at.desc()).limit(limit).all()


def count_unread_in_app(user_id: int) -> int:
    """Count unread in-app notifications for a user."""
    return InAppNotificationModel.query.filter_by(
        user_id=user_id, read_status="UNREAD"
    ).count()


def mark_in_app_read(in_app_id: int, user_id: int) -> InAppNotificationModel:
    """Mark an in-app notification as read."""
    in_app = InAppNotificationModel.query.get(in_app_id)
    if in_app is None:
        raise NotificationError("In-app notification not found.")
    if in_app.user_id != user_id:
        raise NotificationError("Access denied.")
    in_app.read_status = "READ"
    in_app.read_at = datetime.now()
    db.session.commit()
    return in_app


def mark_all_in_app_read(user_id: int) -> int:
    """Mark all in-app notifications as read for a user. Returns count updated."""
    count = InAppNotificationModel.query.filter_by(
        user_id=user_id, read_status="UNREAD"
    ).update(
        {"read_status": "READ", "read_at": datetime.now()},
        synchronize_session=False,
    )
    db.session.commit()
    return count


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _is_channel_enabled(
    user_id: int,
    notification_type: NotificationType,
    channel: NotificationChannel,
) -> bool:
    """Check if a user has enabled a channel for a notification type.

    Mandatory notifications bypass preferences.
    """
    if notification_type in MANDATORY_NOTIFICATION_TYPES:
        return True

    pref = NotificationPreferenceModel.query.filter_by(
        user_id=user_id,
        notification_type=notification_type,
        channel=channel,
    ).first()

    if pref is None:
        return True  # Default: enabled

    return pref.enabled


def _get_recipient_address(user_id: int, channel: NotificationChannel) -> str:
    """Get the recipient address/ID for a channel."""
    user = UserModel.query.get(user_id)
    if user is None:
        return ""

    if channel == NotificationChannel.SMS:
        if user.student_profile and user.student_profile.mobile_phone:
            return user.student_profile.mobile_phone
        if user.teacher_profile and user.teacher_profile.mobile_phone:
            return user.teacher_profile.mobile_phone
        if user.parent_profile and user.parent_profile.mobile_phone:
            return user.parent_profile.mobile_phone
        return ""

    if channel == NotificationChannel.EMAIL:
        return user.login if "@" in user.login else ""

    if channel in (NotificationChannel.TELEGRAM, NotificationChannel.BALE):
        return ""

    return ""


def _send_in_app(
    notification: NotificationModel, delivery: NotificationDeliveryModel
) -> None:
    """Create an in-app notification record."""
    create_in_app_notification(
        user_id=notification.recipient_user_id,
        title=notification.title,
        message=notification.message,
        notification_type=notification.notification_type,
        notification_id=notification.id,
    )
    delivery.status = DeliveryStatus.SENT
    delivery.sent_at = datetime.now()
    delivery.provider_name = "in_app"
    delivery.updated_at = datetime.now()
