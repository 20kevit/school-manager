"""Comprehensive tests for the Notification System (P9)."""

from __future__ import annotations

import pytest

from app import create_app
from app.domain.notification import (
    MANDATORY_NOTIFICATION_TYPES,
    DeliveryStatus,
    InAppNotification,
    Notification,
    NotificationChannel,
    NotificationDelivery,
    NotificationPreference,
    NotificationPriority,
    NotificationStatus,
    NotificationTemplate,
    NotificationType,
    ReadStatus,
)
from app.extensions import db as _db
from app.infrastructure.database.models import (
    RoleModel,
    StudentProfileModel,
    UserModel,
)
from app.infrastructure.notification.providers import (
    NullProvider,
)
from app.infrastructure.notification.registry import (
    get_all_providers,
    get_provider,
    get_provider_health,
    init_default_providers,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def app():
    app = create_app("testing")
    return app


@pytest.fixture(scope="function")
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def admin_user(db):
    user = UserModel(login="admin_notif_test")
    user.set_password("pass123")
    role = RoleModel(name="ADMIN")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def student_user(db):
    from datetime import date

    user = UserModel(login="student_notif_test")
    user.set_password("pass123")
    role = RoleModel(name="STUDENT")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.flush()
    profile = StudentProfileModel(
        user_id=user.id,
        first_name="Ali",
        last_name="Rezaei",
        national_id="1111111111",
        mobile_phone="09121111111",
        birth_date=date(2000, 1, 15),
        gender="MALE",
    )
    db.session.add(profile)
    db.session.commit()
    return user


@pytest.fixture
def teacher_user(db):
    user = UserModel(login="teacher_notif_test")
    user.set_password("pass123")
    role = RoleModel(name="TEACHER")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def parent_user(db):
    user = UserModel(login="parent_notif_test")
    user.set_password("pass123")
    role = RoleModel(name="PARENT")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user


# ---------------------------------------------------------------------------
# Domain Entity Tests
# ---------------------------------------------------------------------------


class TestNotificationDomain:
    def test_notification_creation(self):
        n = Notification(
            id=1,
            notification_type=NotificationType.WELCOME,
            title="Welcome",
            message="Hello!",
            recipient_user_id=1,
        )
        assert n.id == 1
        assert n.status == NotificationStatus.PENDING
        assert n.priority == NotificationPriority.NORMAL

    def test_notification_repr(self):
        n = Notification(
            id=1,
            notification_type=NotificationType.WELCOME,
            title="Welcome",
            message="Hello!",
            recipient_user_id=1,
        )
        assert "Notification" in repr(n)

    def test_delivery_creation(self):
        d = NotificationDelivery(
            id=1,
            notification_id=1,
            channel=NotificationChannel.SMS,
        )
        assert d.status == DeliveryStatus.PENDING
        assert d.attempt_count == 0

    def test_template_creation(self):
        t = NotificationTemplate(
            id=1,
            name="welcome_template",
            notification_type=NotificationType.WELCOME,
            channel=NotificationChannel.IN_APP,
            body="Hello {{ name }}!",
        )
        assert t.is_active is True

    def test_template_render(self):
        t = NotificationTemplate(
            id=1,
            name="test",
            notification_type=NotificationType.WELCOME,
            channel=NotificationChannel.IN_APP,
            subject="Hi {{ name }}",
            body="Welcome {{ name }} to {{ place }}!",
        )
        subject, body = t.render({"name": "Ali", "place": "Academy"})
        assert subject == "Hi Ali"
        assert body == "Welcome Ali to Academy!"

    def test_template_render_missing_variable(self):
        t = NotificationTemplate(
            id=1,
            name="test",
            notification_type=NotificationType.WELCOME,
            channel=NotificationChannel.IN_APP,
            body="Hello {{ name }} and {{ missing }}!",
        )
        subject, body = t.render({"name": "Ali"})
        # Missing variables are left as-is (safe rendering)
        assert "Ali" in body
        assert "{{ missing }}" in body

    def test_preference_creation(self):
        p = NotificationPreference(
            id=1,
            user_id=1,
            notification_type=NotificationType.WELCOME,
            channel=NotificationChannel.SMS,
            enabled=False,
        )
        assert p.enabled is False

    def test_in_app_notification_mark_read(self):
        n = InAppNotification(
            id=1,
            user_id=1,
            title="Test",
            message="Hello",
        )
        assert n.read_status == ReadStatus.UNREAD
        n.mark_read()
        assert n.read_status == ReadStatus.READ
        assert n.read_at is not None


# ---------------------------------------------------------------------------
# Notification Status Transitions
# ---------------------------------------------------------------------------


class TestNotificationStatus:
    def test_valid_statuses(self):
        for status in NotificationStatus:
            assert status in [
                NotificationStatus.PENDING,
                NotificationStatus.SENDING,
                NotificationStatus.SENT,
                NotificationStatus.FAILED,
                NotificationStatus.CANCELLED,
            ]

    def test_delivery_statuses(self):
        for status in DeliveryStatus:
            assert status in [
                DeliveryStatus.PENDING,
                DeliveryStatus.SENT,
                DeliveryStatus.FAILED,
            ]


# ---------------------------------------------------------------------------
# Notification Types
# ---------------------------------------------------------------------------


class TestNotificationTypes:
    def test_enrollment_types(self):
        assert NotificationType.ENROLLMENT_SUBMITTED
        assert NotificationType.ENROLLMENT_APPROVED
        assert NotificationType.ENROLLMENT_REJECTED
        assert NotificationType.ENROLLMENT_CANCELLED

    def test_session_types(self):
        assert NotificationType.SESSION_CREATED
        assert NotificationType.SESSION_RESCHEDULED
        assert NotificationType.SESSION_CANCELLED
        assert NotificationType.SESSION_REMINDER

    def test_activity_types(self):
        assert NotificationType.ACTIVITY_CREATED
        assert NotificationType.ACTIVITY_DUE_SOON
        assert NotificationType.ACTIVITY_GRADED

    def test_assessment_types(self):
        assert NotificationType.ASSESSMENT_CREATED
        assert NotificationType.ASSESSMENT_RESCHEDULED
        assert NotificationType.ASSESSMENT_CANCELLED
        assert NotificationType.RESULT_PUBLISHED

    def test_finance_types(self):
        assert NotificationType.TUITION_CHARGED
        assert NotificationType.PAYMENT_RECEIVED
        assert NotificationType.REFUND_ISSUED
        assert NotificationType.BALANCE_CHANGED

    def test_account_types(self):
        assert NotificationType.WELCOME
        assert NotificationType.PASSWORD_CHANGED

    def test_mandatory_types(self):
        assert NotificationType.WELCOME in MANDATORY_NOTIFICATION_TYPES
        assert NotificationType.PASSWORD_CHANGED in MANDATORY_NOTIFICATION_TYPES


# ---------------------------------------------------------------------------
# Provider Tests
# ---------------------------------------------------------------------------


class TestProviders:
    def test_null_provider(self):
        p = NullProvider()
        assert p.is_available() is False
        result = p.send("123", "sub", "body")
        assert result.success is False

    def test_sms_provider_not_configured(self):
        from app.infrastructure.notification.sms_provider import SmsProvider

        p = SmsProvider()
        # Without env vars, should not be available
        assert p.is_available() is False

    def test_sms_configured_never_reports_false_success(self, monkeypatch):
        """A configured-but-unimplemented provider must fail, not fake success."""
        from app.infrastructure.notification.sms_provider import SmsProvider

        monkeypatch.setenv("SMS_API_KEY", "test-key")
        monkeypatch.setenv("SMS_SENDER", "09120000000")
        monkeypatch.setenv("SMS_API_URL", "https://sms.example.invalid/send")
        p = SmsProvider()
        assert p.is_available() is True
        result = p.send("09121234567", "subject", "body")
        assert result.success is False
        assert "not implemented" in result.error

    def test_sms_validate_recipient(self):
        from app.infrastructure.notification.sms_provider import SmsProvider

        p = SmsProvider()
        assert p.validate_recipient("09121234567") is True
        assert p.validate_recipient("12345") is False
        assert p.validate_recipient("0912123456") is False

    def test_telegram_validate_recipient(self):
        from app.infrastructure.notification.telegram_provider import TelegramProvider

        p = TelegramProvider()
        assert p.validate_recipient("123456789") is True
        assert p.validate_recipient("@username") is True
        assert p.validate_recipient("") is False

    def test_bale_validate_recipient(self):
        from app.infrastructure.notification.bale_provider import BaleProvider

        p = BaleProvider()
        assert p.validate_recipient("123456789") is True
        assert p.validate_recipient("") is False

    def test_email_validate_recipient(self):
        from app.infrastructure.notification.email_provider import EmailProvider

        p = EmailProvider()
        assert p.validate_recipient("test@example.com") is True
        assert p.validate_recipient("invalid") is False

    def test_provider_registry(self):
        init_default_providers()
        providers = get_all_providers()
        assert len(providers) >= 4

    def test_get_provider(self):
        init_default_providers()
        p = get_provider("SMS")
        assert p is not None
        p = get_provider("NONEXISTENT")
        assert isinstance(p, NullProvider)

    def test_provider_health(self):
        init_default_providers()
        health = get_provider_health()
        assert len(health) >= 4
        for h in health:
            assert "name" in h
            assert "channel" in h
            assert "available" in h


# ---------------------------------------------------------------------------
# Template Service Tests
# ---------------------------------------------------------------------------


class TestTemplateService:
    def test_create_template(self, db):
        from app.application.notification.template_service import (
            create_template,
            get_template,
        )

        t = create_template(
            name="test_welcome",
            notification_type=NotificationType.WELCOME,
            channel=NotificationChannel.IN_APP,
            body="Hello {{ name }}!",
        )
        assert t.id is not None
        fetched = get_template(t.id)
        assert fetched is not None
        assert fetched.name == "test_welcome"

    def test_create_duplicate_template(self, db):
        from app.application.notification.template_service import (
            TemplateError,
            create_template,
        )

        create_template(
            name="dup_test",
            notification_type=NotificationType.WELCOME,
            channel=NotificationChannel.IN_APP,
            body="Hello!",
        )
        with pytest.raises(TemplateError):
            create_template(
                name="dup_test",
                notification_type=NotificationType.WELCOME,
                channel=NotificationChannel.IN_APP,
                body="Hello!",
            )

    def test_update_template(self, db):
        from app.application.notification.template_service import (
            create_template,
            update_template,
        )

        t = create_template(
            name="update_test",
            notification_type=NotificationType.WELCOME,
            channel=NotificationChannel.IN_APP,
            body="Original",
        )
        updated = update_template(t.id, body="Updated")
        assert updated.body == "Updated"

    def test_delete_template(self, db):
        from app.application.notification.template_service import (
            create_template,
            delete_template,
            get_template,
        )

        t = create_template(
            name="delete_test",
            notification_type=NotificationType.WELCOME,
            channel=NotificationChannel.IN_APP,
            body="Delete me",
        )
        delete_template(t.id)
        assert get_template(t.id) is None

    def test_list_templates(self, db):
        from app.application.notification.template_service import (
            create_template,
            list_templates,
        )

        create_template(
            name="list_test_1",
            notification_type=NotificationType.WELCOME,
            channel=NotificationChannel.IN_APP,
            body="Body 1",
        )
        create_template(
            name="list_test_2",
            notification_type=NotificationType.WELCOME,
            channel=NotificationChannel.SMS,
            body="Body 2",
        )
        all_templates = list_templates()
        assert len(all_templates) >= 2

    def test_render_template(self, db):
        from app.application.notification.template_service import (
            create_template,
            render_template,
        )

        t = create_template(
            name="render_test",
            notification_type=NotificationType.WELCOME,
            channel=NotificationChannel.IN_APP,
            subject="Hi {{ name }}",
            body="Welcome {{ name }}!",
        )
        subject, body = render_template(t.id, {"name": "Ali"})
        assert subject == "Hi Ali"
        assert body == "Welcome Ali!"

    def test_render_inactive_template(self, db):
        from app.application.notification.template_service import (
            TemplateError,
            create_template,
            render_template,
            update_template,
        )

        t = create_template(
            name="inactive_test",
            notification_type=NotificationType.WELCOME,
            channel=NotificationChannel.IN_APP,
            body="Hello",
        )
        update_template(t.id, is_active=False)
        with pytest.raises(TemplateError):
            render_template(t.id, {})


# ---------------------------------------------------------------------------
# Notification Service Tests
# ---------------------------------------------------------------------------


class TestNotificationService:
    def test_create_notification(self, db, student_user):
        from app.application.notification.notification_service import (
            create_notification,
            get_notification,
        )

        n = create_notification(
            notification_type=NotificationType.WELCOME,
            title="Welcome",
            message="Hello!",
            recipient_user_id=student_user.id,
            channels=[NotificationChannel.IN_APP],
        )
        assert n.id is not None
        fetched = get_notification(n.id)
        assert fetched is not None

    def test_send_in_app_notification(self, db, student_user):
        from app.application.notification.notification_service import (
            create_notification,
            send_notification,
        )

        n = create_notification(
            notification_type=NotificationType.WELCOME,
            title="Welcome",
            message="Hello!",
            recipient_user_id=student_user.id,
            channels=[NotificationChannel.IN_APP],
        )
        sent = send_notification(n.id)
        assert sent.status == NotificationStatus.SENT

    def test_cancel_notification(self, db, student_user):
        from app.application.notification.notification_service import (
            cancel_notification,
            create_notification,
        )

        n = create_notification(
            notification_type=NotificationType.WELCOME,
            title="Welcome",
            message="Hello!",
            recipient_user_id=student_user.id,
            channels=[NotificationChannel.IN_APP],
        )
        cancelled = cancel_notification(n.id)
        assert cancelled.status == NotificationStatus.CANCELLED

    def test_retry_notification(self, db, student_user):
        from app.application.notification.notification_service import (
            create_notification,
            retry_notification,
        )

        n = create_notification(
            notification_type=NotificationType.WELCOME,
            title="Welcome",
            message="Hello!",
            recipient_user_id=student_user.id,
            channels=[NotificationChannel.IN_APP],
        )
        # Simulate failure
        n.status = NotificationStatus.FAILED
        _db.session.commit()

        retried = retry_notification(n.id)
        assert retried.status == NotificationStatus.SENT

    def test_send_manual_notification(self, db, student_user):
        from app.application.notification.notification_service import (
            send_manual_notification,
        )

        notifications = send_manual_notification(
            recipient_user_ids=[student_user.id],
            channel=NotificationChannel.IN_APP,
            title="Manual",
            message="Test manual notification",
        )
        assert len(notifications) == 1

    def test_send_announcement(self, db, student_user, teacher_user):
        from app.application.notification.notification_service import (
            send_announcement,
        )

        notifications = send_announcement(
            title="Announcement",
            message="System update",
            channels=[NotificationChannel.IN_APP],
            recipient_user_ids=[student_user.id, teacher_user.id],
        )
        assert len(notifications) == 2

    def test_list_notifications(self, db, student_user):
        from app.application.notification.notification_service import (
            create_notification,
            list_notifications,
        )

        create_notification(
            notification_type=NotificationType.WELCOME,
            title="Welcome",
            message="Hello!",
            recipient_user_id=student_user.id,
            channels=[NotificationChannel.IN_APP],
        )
        notifications = list_notifications(recipient_user_id=student_user.id)
        assert len(notifications) >= 1

    def test_count_notifications(self, db, student_user):
        from app.application.notification.notification_service import (
            count_notifications,
            create_notification,
        )

        create_notification(
            notification_type=NotificationType.WELCOME,
            title="Welcome",
            message="Hello!",
            recipient_user_id=student_user.id,
            channels=[NotificationChannel.IN_APP],
        )
        count = count_notifications(recipient_user_id=student_user.id)
        assert count >= 1


# ---------------------------------------------------------------------------
# In-App Notification Tests
# ---------------------------------------------------------------------------


class TestInAppNotifications:
    def test_create_in_app(self, db, student_user):
        from app.application.notification.notification_service import (
            create_in_app_notification,
        )

        n = create_in_app_notification(
            user_id=student_user.id,
            title="Test",
            message="Hello",
        )
        assert n.read_status == "UNREAD"

    def test_get_in_app_notifications(self, db, student_user):
        from app.application.notification.notification_service import (
            create_in_app_notification,
            get_user_in_app_notifications,
        )

        create_in_app_notification(
            user_id=student_user.id,
            title="Test",
            message="Hello",
        )
        notifications = get_user_in_app_notifications(student_user.id)
        assert len(notifications) == 1

    def test_count_unread(self, db, student_user):
        from app.application.notification.notification_service import (
            count_unread_in_app,
            create_in_app_notification,
        )

        create_in_app_notification(
            user_id=student_user.id,
            title="Test",
            message="Hello",
        )
        assert count_unread_in_app(student_user.id) == 1

    def test_mark_read(self, db, student_user):
        from app.application.notification.notification_service import (
            create_in_app_notification,
            mark_in_app_read,
        )

        n = create_in_app_notification(
            user_id=student_user.id,
            title="Test",
            message="Hello",
        )
        marked = mark_in_app_read(n.id, student_user.id)
        assert marked.read_status == "READ"

    def test_mark_read_wrong_user(self, db, student_user, teacher_user):
        from app.application.notification.notification_service import (
            NotificationError,
            create_in_app_notification,
            mark_in_app_read,
        )

        n = create_in_app_notification(
            user_id=student_user.id,
            title="Test",
            message="Hello",
        )
        with pytest.raises(NotificationError):
            mark_in_app_read(n.id, teacher_user.id)

    def test_mark_all_read(self, db, student_user):
        from app.application.notification.notification_service import (
            create_in_app_notification,
            mark_all_in_app_read,
        )

        create_in_app_notification(
            user_id=student_user.id,
            title="Test 1",
            message="Hello 1",
        )
        create_in_app_notification(
            user_id=student_user.id,
            title="Test 2",
            message="Hello 2",
        )
        count = mark_all_in_app_read(student_user.id)
        assert count == 2


# ---------------------------------------------------------------------------
# Preference Service Tests
# ---------------------------------------------------------------------------


class TestPreferenceService:
    def test_default_preferences(self, db, student_user):
        from app.application.notification.preference_service import is_channel_enabled

        enabled = is_channel_enabled(
            student_user.id,
            NotificationType.WELCOME,
            NotificationChannel.SMS,
        )
        assert enabled is True

    def test_disable_preference(self, db, student_user):
        from app.application.notification.preference_service import (
            is_channel_enabled,
            update_preference,
        )

        update_preference(
            user_id=student_user.id,
            notification_type=NotificationType.ANNOUNCEMENT,
            channel=NotificationChannel.SMS,
            enabled=False,
        )
        enabled = is_channel_enabled(
            student_user.id,
            NotificationType.ANNOUNCEMENT,
            NotificationChannel.SMS,
        )
        assert enabled is False

    def test_mandatory_bypasses_preference(self, db, student_user):
        from app.application.notification.preference_service import (
            is_channel_enabled,
            update_preference,
        )

        update_preference(
            user_id=student_user.id,
            notification_type=NotificationType.WELCOME,
            channel=NotificationChannel.SMS,
            enabled=False,
        )
        enabled = is_channel_enabled(
            student_user.id,
            NotificationType.WELCOME,
            NotificationChannel.SMS,
        )
        assert enabled is True

    def test_get_preference_matrix(self, db, student_user):
        from app.application.notification.preference_service import (
            get_preference_matrix,
            update_preference,
        )

        update_preference(
            user_id=student_user.id,
            notification_type=NotificationType.ANNOUNCEMENT,
            channel=NotificationChannel.SMS,
            enabled=False,
        )
        matrix = get_preference_matrix(student_user.id)
        assert "ANNOUNCEMENT" in matrix
        assert matrix["ANNOUNCEMENT"]["SMS"] is False


# ---------------------------------------------------------------------------
# Event Handler Tests
# ---------------------------------------------------------------------------


class TestEventHandlers:
    def test_on_enrollment_approved(self, db, student_user):
        from app.application.notification.event_handlers import on_enrollment_approved

        on_enrollment_approved(student_user.id, "Test Class")
        # Should create notification without error

    def test_on_enrollment_rejected(self, db, student_user):
        from app.application.notification.event_handlers import on_enrollment_rejected

        on_enrollment_rejected(student_user.id, "Test Class")

    def test_on_enrollment_cancelled(self, db, student_user):
        from app.application.notification.event_handlers import on_enrollment_cancelled

        on_enrollment_cancelled(student_user.id, "Test Class")

    def test_on_payment_received(self, db, student_user):
        from app.application.notification.event_handlers import on_payment_received

        on_payment_received(student_user.id, "1,000,000")

    def test_on_welcome(self, db, student_user):
        from app.application.notification.event_handlers import on_welcome

        on_welcome(student_user.id)

    def test_on_password_changed(self, db, student_user):
        from app.application.notification.event_handlers import on_password_changed

        on_password_changed(student_user.id)


# ---------------------------------------------------------------------------
# Multi-Channel Delivery Tests
# ---------------------------------------------------------------------------


class TestMultiChannel:
    def test_multi_channel_send(self, db, student_user):
        from app.application.notification.notification_service import (
            send_multi_channel_notification,
        )

        n = send_multi_channel_notification(
            notification_type=NotificationType.WELCOME,
            title="Welcome",
            message="Hello!",
            recipient_user_id=student_user.id,
            channels=[NotificationChannel.IN_APP, NotificationChannel.SMS],
        )
        assert n.status == NotificationStatus.SENT

    def test_delivery_records_created(self, db, student_user):
        from app.application.notification.notification_service import (
            create_notification,
            get_notification_deliveries,
        )

        n = create_notification(
            notification_type=NotificationType.WELCOME,
            title="Welcome",
            message="Hello!",
            recipient_user_id=student_user.id,
            channels=[NotificationChannel.IN_APP, NotificationChannel.SMS],
        )
        deliveries = get_notification_deliveries(n.id)
        assert len(deliveries) == 2


# ---------------------------------------------------------------------------
# Duplicate Prevention (Event Key) Tests
# ---------------------------------------------------------------------------


class TestDuplicatePrevention:
    def test_event_key_stored(self, db, student_user):
        from app.application.notification.notification_service import (
            create_notification,
        )

        n = create_notification(
            notification_type=NotificationType.WELCOME,
            title="Welcome",
            message="Hello!",
            recipient_user_id=student_user.id,
            channels=[NotificationChannel.IN_APP],
            event_key="welcome:1:student",
        )
        assert n.event_key == "welcome:1:student"


# ---------------------------------------------------------------------------
# Authorization Tests
# ---------------------------------------------------------------------------


class TestNotificationAuthorization:
    def test_student_sees_own_notifications(self, db, student_user, teacher_user):
        from app.application.notification.notification_service import (
            create_in_app_notification,
            get_user_in_app_notifications,
        )

        create_in_app_notification(
            user_id=student_user.id, title="Student notif", message="Hi"
        )
        create_in_app_notification(
            user_id=teacher_user.id, title="Teacher notif", message="Hi"
        )
        student_notifs = get_user_in_app_notifications(student_user.id)
        teacher_notifs = get_user_in_app_notifications(teacher_user.id)
        assert len(student_notifs) == 1
        assert student_notifs[0].title == "Student notif"
        assert len(teacher_notifs) == 1
        assert teacher_notifs[0].title == "Teacher notif"


# ---------------------------------------------------------------------------
# Web Route Tests
# ---------------------------------------------------------------------------


class TestNotificationRoutes:
    def _login(self, client, user):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)
            sess["user_id"] = str(user.id)
            sess["_fresh"] = True

    def test_admin_dashboard(self, client, db, admin_user):
        self._login(client, admin_user)
        resp = client.get("/notification/admin")
        assert resp.status_code == 200

    def test_admin_manual(self, client, db, admin_user):
        self._login(client, admin_user)
        resp = client.get("/notification/admin/manual")
        assert resp.status_code == 200

    def test_admin_announcement(self, client, db, admin_user):
        self._login(client, admin_user)
        resp = client.get("/notification/admin/announcement")
        assert resp.status_code == 200

    def test_admin_templates(self, client, db, admin_user):
        self._login(client, admin_user)
        resp = client.get("/notification/admin/templates")
        assert resp.status_code == 200

    def test_student_notifications(self, client, db, student_user):
        self._login(client, student_user)
        resp = client.get("/notification/my")
        assert resp.status_code == 200

    def test_student_preferences(self, client, db, student_user):
        self._login(client, student_user)
        resp = client.get("/notification/preferences")
        assert resp.status_code == 200

    def test_unauthenticated_redirect(self, client, db):
        resp = client.get("/notification/my")
        assert resp.status_code in (302, 401)
