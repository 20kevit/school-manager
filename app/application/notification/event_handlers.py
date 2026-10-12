"""Event handlers — trigger notifications from application events."""

from __future__ import annotations

import logging

from app.domain.notification import (
    NotificationChannel,
    NotificationPriority,
    NotificationType,
)

logger = logging.getLogger(__name__)


def _send(notification_type, title, message, recipient_id, **kwargs):
    """Lazy import and send to avoid circular imports."""
    from app.application.notification.notification_service import (
        send_multi_channel_notification,
    )

    channels = kwargs.pop("channels", [NotificationChannel.IN_APP])
    priority = kwargs.pop("priority", NotificationPriority.NORMAL)
    event_key = kwargs.pop("event_key", None)
    try:
        send_multi_channel_notification(
            notification_type=notification_type,
            title=title,
            message=message,
            recipient_user_id=recipient_id,
            channels=channels,
            priority=priority,
            event_key=event_key,
        )
    except Exception:
        logger.exception("Failed to send notification: %s", title)


# ---------------------------------------------------------------------------
# Enrollment events
# ---------------------------------------------------------------------------


def on_enrollment_submitted(student_user_id: int, class_title: str) -> None:
    """Notify admin about new enrollment request."""

    _send(
        notification_type=NotificationType.ENROLLMENT_SUBMITTED,
        title="درخواست ثبت‌نام جدید",
        message=f"درخواست ثبت‌نام جدید برای کلاس {class_title} ثبت شد.",
        recipient_id=_get_admin_user_id(),
        channels=[NotificationChannel.IN_APP],
        priority=NotificationPriority.HIGH,
        event_key=f"enrollment_submitted:{student_user_id}:{class_title}",
    )


def on_enrollment_approved(student_user_id: int, class_title: str) -> None:
    """Notify student about enrollment approval."""

    _send(
        notification_type=NotificationType.ENROLLMENT_APPROVED,
        title="تأیید ثبت‌نام",
        message=f"ثبت‌نام شما در کلاس {class_title} تأیید شد.",
        recipient_id=student_user_id,
        channels=[NotificationChannel.IN_APP, NotificationChannel.SMS],
        event_key=f"enrollment_approved:{student_user_id}:{class_title}",
    )


def on_enrollment_rejected(student_user_id: int, class_title: str) -> None:
    """Notify student about enrollment rejection."""
    _send(
        notification_type=NotificationType.ENROLLMENT_REJECTED,
        title="رد ثبت‌نام",
        message=f"ثبت‌نام شما در کلاس {class_title} رد شد.",
        recipient_id=student_user_id,
        channels=[NotificationChannel.IN_APP],
        event_key=f"enrollment_rejected:{student_user_id}:{class_title}",
    )


def on_enrollment_cancelled(student_user_id: int, class_title: str) -> None:
    """Notify student about enrollment cancellation."""
    _send(
        notification_type=NotificationType.ENROLLMENT_CANCELLED,
        title="لغو ثبت‌نام",
        message=f"ثبت‌نام شما در کلاس {class_title} لغو شد.",
        recipient_id=student_user_id,
        channels=[NotificationChannel.IN_APP],
        event_key=f"enrollment_cancelled:{student_user_id}:{class_title}",
    )


# ---------------------------------------------------------------------------
# Session events
# ---------------------------------------------------------------------------


def on_session_created(class_id: int, session_number: int, date_str: str) -> None:
    """Notify enrolled students and teacher about new session."""
    from app.infrastructure.database.models import (
        AcademyClassModel,
        EnrollmentModel,
    )

    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        return

    enrollments = EnrollmentModel.query.filter_by(
        class_id=class_id, status="APPROVED"
    ).all()

    for enrollment in enrollments:
        _send(
            notification_type=NotificationType.SESSION_CREATED,
            title="جلسه جدید",
            message=f"جلسه شماره {session_number} کلاس {academy_class.title} در تاریخ {date_str} ایجاد شد.",
            recipient_id=enrollment.student_user_id,
            channels=[NotificationChannel.IN_APP],
            event_key=f"session_created:{class_id}:{session_number}",
        )

    if academy_class.teacher_user_id:
        _send(
            notification_type=NotificationType.SESSION_CREATED,
            title="جلسه جدید",
            message=f"جلسه شماره {session_number} کلاس {academy_class.title} در تاریخ {date_str} ایجاد شد.",
            recipient_id=academy_class.teacher_user_id,
            channels=[NotificationChannel.IN_APP],
            event_key=f"session_created_teacher:{class_id}:{session_number}",
        )


def on_session_cancelled(class_id: int, session_number: int) -> None:
    """Notify about session cancellation."""
    from app.infrastructure.database.models import (
        AcademyClassModel,
        EnrollmentModel,
    )

    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        return

    enrollments = EnrollmentModel.query.filter_by(
        class_id=class_id, status="APPROVED"
    ).all()

    for enrollment in enrollments:
        _send(
            notification_type=NotificationType.SESSION_CANCELLED,
            title="لغو جلسه",
            message=f"جلسه شماره {session_number} کلاس {academy_class.title} لغو شد.",
            recipient_id=enrollment.student_user_id,
            channels=[NotificationChannel.IN_APP, NotificationChannel.SMS],
            priority=NotificationPriority.HIGH,
            event_key=f"session_cancelled:{class_id}:{session_number}",
        )

    if academy_class.teacher_user_id:
        _send(
            notification_type=NotificationType.SESSION_CANCELLED,
            title="لغو جلسه",
            message=f"جلسه شماره {session_number} کلاس {academy_class.title} لغو شد.",
            recipient_id=academy_class.teacher_user_id,
            channels=[NotificationChannel.IN_APP],
            priority=NotificationPriority.HIGH,
            event_key=f"session_cancelled_teacher:{class_id}:{session_number}",
        )


def on_session_rescheduled(
    class_id: int, session_number: int, new_date_str: str
) -> None:
    """Notify about session rescheduling."""
    from app.infrastructure.database.models import (
        AcademyClassModel,
        EnrollmentModel,
    )

    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        return

    enrollments = EnrollmentModel.query.filter_by(
        class_id=class_id, status="APPROVED"
    ).all()

    for enrollment in enrollments:
        _send(
            notification_type=NotificationType.SESSION_RESCHEDULED,
            title="تغییر زمان جلسه",
            message=f"زمان جلسه شماره {session_number} کلاس {academy_class.title} به {new_date_str} تغییر کرد.",
            recipient_id=enrollment.student_user_id,
            channels=[NotificationChannel.IN_APP],
            event_key=f"session_rescheduled:{class_id}:{session_number}",
        )


# ---------------------------------------------------------------------------
# Activity events
# ---------------------------------------------------------------------------


def on_activity_created(
    activity_title: str, class_id: int, recipient_ids: list[int]
) -> None:
    """Notify about new activity."""
    from app.infrastructure.database.models import AcademyClassModel

    academy_class = AcademyClassModel.query.get(class_id)
    class_name = academy_class.title if academy_class else ""

    for recipient_id in recipient_ids:
        _send(
            notification_type=NotificationType.ACTIVITY_CREATED,
            title="فعالیت جدید",
            message=f"فعالیت '{activity_title}' در کلاس {class_name} ایجاد شد.",
            recipient_id=recipient_id,
            channels=[NotificationChannel.IN_APP],
            event_key=f"activity_created:{activity_title}:{class_id}",
        )


def on_activity_graded(student_user_id: int, activity_title: str, score: str) -> None:
    """Notify student about graded activity."""
    _send(
        notification_type=NotificationType.ACTIVITY_GRADED,
        title="نمره فعالیت",
        message=f"فعالیت '{activity_title}' نمره {score} دریافت کرد.",
        recipient_id=student_user_id,
        channels=[NotificationChannel.IN_APP],
        event_key=f"activity_graded:{student_user_id}:{activity_title}",
    )


# ---------------------------------------------------------------------------
# Assessment events
# ---------------------------------------------------------------------------


def on_assessment_created(
    assessment_title: str, class_id: int, recipient_ids: list[int]
) -> None:
    """Notify about new assessment."""
    from app.infrastructure.database.models import AcademyClassModel

    academy_class = AcademyClassModel.query.get(class_id)
    class_name = academy_class.title if academy_class else ""

    for recipient_id in recipient_ids:
        _send(
            notification_type=NotificationType.ASSESSMENT_CREATED,
            title="آزمون جدید",
            message=f"آزمون '{assessment_title}' در کلاس {class_name} ایجاد شد.",
            recipient_id=recipient_id,
            channels=[NotificationChannel.IN_APP],
            event_key=f"assessment_created:{assessment_title}:{class_id}",
        )


def on_result_published(
    student_user_id: int, assessment_title: str, score: str
) -> None:
    """Notify student about published result."""
    _send(
        notification_type=NotificationType.RESULT_PUBLISHED,
        title="انتشار نتیجه",
        message=f"نتیجه آزمون '{assessment_title}' منتشر شد. نمره: {score}",
        recipient_id=student_user_id,
        channels=[NotificationChannel.IN_APP],
        event_key=f"result_published:{student_user_id}:{assessment_title}",
    )


# ---------------------------------------------------------------------------
# Finance events
# ---------------------------------------------------------------------------


def on_tuition_charged(student_user_id: int, amount: str, class_title: str) -> None:
    """Notify student about tuition charge."""
    _send(
        notification_type=NotificationType.TUITION_CHARGED,
        title="شهریه ثبت شد",
        message=f"شهریه {amount} تومان برای کلاس {class_title} ثبت شد.",
        recipient_id=student_user_id,
        channels=[NotificationChannel.IN_APP],
        event_key=f"tuition_charged:{student_user_id}:{class_title}",
    )


def on_payment_received(student_user_id: int, amount: str) -> None:
    """Notify student about payment receipt."""
    _send(
        notification_type=NotificationType.PAYMENT_RECEIVED,
        title="پرداخت تأیید شد",
        message=f"پرداخت {amount} تومان تأیید شد.",
        recipient_id=student_user_id,
        channels=[NotificationChannel.IN_APP, NotificationChannel.SMS],
        priority=NotificationPriority.HIGH,
        event_key=f"payment_received:{student_user_id}:{amount}",
    )


def on_refund_issued(student_user_id: int, amount: str) -> None:
    """Notify student about refund."""
    _send(
        notification_type=NotificationType.REFUND_ISSUED,
        title="بازپرداخت انجام شد",
        message=f"بازپرداخت {amount} تومان انجام شد.",
        recipient_id=student_user_id,
        channels=[NotificationChannel.IN_APP],
        event_key=f"refund_issued:{student_user_id}:{amount}",
    )


# ---------------------------------------------------------------------------
# Account events
# ---------------------------------------------------------------------------


def on_welcome(student_user_id: int) -> None:
    """Send welcome notification to new user."""
    _send(
        notification_type=NotificationType.WELCOME,
        title="خوش آمدید",
        message="حساب کاربری شما با موفقیت ایجاد شد.",
        recipient_id=student_user_id,
        channels=[NotificationChannel.IN_APP],
    )


def on_password_changed(user_id: int) -> None:
    """Notify user about password change."""
    _send(
        notification_type=NotificationType.PASSWORD_CHANGED,
        title="تغییر رمز عبور",
        message="رمز عبور شما تغییر کرد.",
        recipient_id=user_id,
        channels=[NotificationChannel.IN_APP],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_admin_user_id() -> int:
    """Get the first admin user ID."""
    from app.infrastructure.database.models import UserModel

    admin = UserModel.query.filter(UserModel.roles.any(name="ADMIN")).first()
    return admin.id if admin else 0
