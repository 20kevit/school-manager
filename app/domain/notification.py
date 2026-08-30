from __future__ import annotations

from datetime import datetime
from enum import StrEnum


class NotificationChannel(StrEnum):
    """Delivery channel for a notification."""

    SMS = "SMS"
    TELEGRAM = "TELEGRAM"
    BALE = "BALE"
    EMAIL = "EMAIL"
    IN_APP = "IN_APP"


class NotificationStatus(StrEnum):
    """Lifecycle status of a notification."""

    PENDING = "PENDING"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class NotificationPriority(StrEnum):
    """Priority level for a notification."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class NotificationType(StrEnum):
    """Type/category of notification event."""

    # Enrollment
    ENROLLMENT_SUBMITTED = "ENROLLMENT_SUBMITTED"
    ENROLLMENT_APPROVED = "ENROLLMENT_APPROVED"
    ENROLLMENT_REJECTED = "ENROLLMENT_REJECTED"
    ENROLLMENT_CANCELLED = "ENROLLMENT_CANCELLED"

    # Classes / Sessions
    SESSION_CREATED = "SESSION_CREATED"
    SESSION_RESCHEDULED = "SESSION_RESCHEDULED"
    SESSION_CANCELLED = "SESSION_CANCELLED"
    SESSION_REMINDER = "SESSION_REMINDER"

    # Activities
    ACTIVITY_CREATED = "ACTIVITY_CREATED"
    ACTIVITY_DUE_SOON = "ACTIVITY_DUE_SOON"
    ACTIVITY_GRADED = "ACTIVITY_GRADED"

    # Assessments
    ASSESSMENT_CREATED = "ASSESSMENT_CREATED"
    ASSESSMENT_RESCHEDULED = "ASSESSMENT_RESCHEDULED"
    ASSESSMENT_CANCELLED = "ASSESSMENT_CANCELLED"
    RESULT_PUBLISHED = "RESULT_PUBLISHED"

    # Finance
    TUITION_CHARGED = "TUITION_CHARGED"
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    REFUND_ISSUED = "REFUND_ISSUED"
    BALANCE_CHANGED = "BALANCE_CHANGED"

    # Account
    WELCOME = "WELCOME"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"

    # General
    ANNOUNCEMENT = "ANNOUNCEMENT"

    # In-App
    IN_APP_MESSAGE = "IN_APP_MESSAGE"


# Notification types that are mandatory (ignore user preferences)
MANDATORY_NOTIFICATION_TYPES = frozenset(
    {
        NotificationType.WELCOME,
        NotificationType.PASSWORD_CHANGED,
    }
)


class DeliveryStatus(StrEnum):
    """Status of an individual delivery attempt."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class ReadStatus(StrEnum):
    """Read status for in-app notifications."""

    UNREAD = "UNREAD"
    READ = "READ"


class Notification:
    """Notification domain entity."""

    def __init__(
        self,
        id: int | None,
        notification_type: NotificationType,
        title: str,
        message: str,
        recipient_user_id: int,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        template_id: int | None = None,
        event_key: str | None = None,
        status: NotificationStatus = NotificationStatus.PENDING,
        scheduled_at: datetime | None = None,
        sent_at: datetime | None = None,
        failed_at: datetime | None = None,
        failure_reason: str = "",
        retry_count: int = 0,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.notification_type = notification_type
        self.title = title
        self.message = message
        self.recipient_user_id = recipient_user_id
        self.priority = priority
        self.template_id = template_id
        self.event_key = event_key
        self.status = status
        self.scheduled_at = scheduled_at
        self.sent_at = sent_at
        self.failed_at = failed_at
        self.failure_reason = failure_reason
        self.retry_count = retry_count
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def __repr__(self) -> str:
        return (
            f"<Notification id={self.id} type={self.notification_type} "
            f"recipient={self.recipient_user_id} status={self.status}>"
        )


class NotificationDelivery:
    """Individual delivery record for a notification on a specific channel."""

    def __init__(
        self,
        id: int | None,
        notification_id: int,
        channel: NotificationChannel,
        status: DeliveryStatus = DeliveryStatus.PENDING,
        provider_name: str = "",
        provider_message_id: str = "",
        failure_reason: str = "",
        attempt_count: int = 0,
        sent_at: datetime | None = None,
        failed_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.notification_id = notification_id
        self.channel = channel
        self.status = status
        self.provider_name = provider_name
        self.provider_message_id = provider_message_id
        self.failure_reason = failure_reason
        self.attempt_count = attempt_count
        self.sent_at = sent_at
        self.failed_at = failed_at
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def __repr__(self) -> str:
        return (
            f"<NotificationDelivery id={self.id} notification={self.notification_id} "
            f"channel={self.channel} status={self.status}>"
        )


class NotificationTemplate:
    """Reusable notification template domain entity."""

    def __init__(
        self,
        id: int | None,
        name: str,
        notification_type: NotificationType,
        channel: NotificationChannel,
        subject: str = "",
        body: str = "",
        is_active: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.name = name
        self.notification_type = notification_type
        self.channel = channel
        self.subject = subject
        self.body = body
        self.is_active = is_active
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def render(self, context: dict[str, str]) -> tuple[str, str]:
        """Render template with context variables.

        Returns (subject, body) with variables replaced.
        Missing variables are replaced with empty string.
        """
        subject = self.subject
        body = self.body
        for key, value in context.items():
            placeholder = "{{ " + key + " }}"
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
        return subject, body

    def __repr__(self) -> str:
        return (
            f"<NotificationTemplate id={self.id} name={self.name!r} "
            f"type={self.notification_type} channel={self.channel}>"
        )


class NotificationPreference:
    """User notification preference domain entity."""

    def __init__(
        self,
        id: int | None,
        user_id: int,
        notification_type: NotificationType,
        channel: NotificationChannel,
        enabled: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.user_id = user_id
        self.notification_type = notification_type
        self.channel = channel
        self.enabled = enabled
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def __repr__(self) -> str:
        return (
            f"<NotificationPreference id={self.id} user={self.user_id} "
            f"type={self.notification_type} channel={self.channel} "
            f"enabled={self.enabled}>"
        )


class InAppNotification:
    """In-app notification domain entity."""

    def __init__(
        self,
        id: int | None,
        user_id: int,
        notification_id: int | None = None,
        title: str = "",
        message: str = "",
        notification_type: NotificationType = NotificationType.IN_APP_MESSAGE,
        link: str = "",
        read_status: ReadStatus = ReadStatus.UNREAD,
        read_at: datetime | None = None,
        created_at: datetime | None = None,
    ):
        self.id = id
        self.user_id = user_id
        self.notification_id = notification_id
        self.title = title
        self.message = message
        self.notification_type = notification_type
        self.link = link
        self.read_status = read_status
        self.read_at = read_at
        self.created_at = created_at or datetime.now()

    def mark_read(self) -> None:
        """Mark notification as read."""
        self.read_status = ReadStatus.READ
        self.read_at = datetime.now()

    def __repr__(self) -> str:
        return (
            f"<InAppNotification id={self.id} user={self.user_id} "
            f"read={self.read_status}>"
        )
