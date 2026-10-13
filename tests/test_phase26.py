"""Tests for P26 — Automated Tasks & Audit Logging."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from app import create_app
from app.extensions import db as _db
from app.infrastructure.database.models import (
    AcademyClassModel,
    AssessmentModel,
    AuditLogModel,
    CourseModel,
    EnrollmentModel,
    FinancialTransactionModel,
    RoleModel,
    SessionModel,
    StudentProfileModel,
    TeacherProfileModel,
    UserModel,
)


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
    user = UserModel(login="admin")
    user.set_password("adminpass")
    role = RoleModel(name="ADMIN")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def teacher_user(db):
    user = UserModel(login="teacher")
    user.set_password("teacherpass")
    role = RoleModel(name="TEACHER")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.flush()
    profile = TeacherProfileModel(
        user_id=user.id,
        first_name="Teacher",
        last_name="One",
        national_id="T1234567890",
        mobile_phone="09120000001",
    )
    db.session.add(profile)
    db.session.commit()
    return user


@pytest.fixture
def student_user(db):
    user = UserModel(login="student")
    user.set_password("studentpass")
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
        national_id="1234567890",
        mobile_phone="09121234567",
        birth_date=date(2000, 1, 15),
        gender="MALE",
    )
    db.session.add(profile)
    db.session.commit()
    return user


@pytest.fixture
def course(db):
    c = CourseModel(title="Test Course", num_sessions=5)
    db.session.add(c)
    db.session.commit()
    return c


@pytest.fixture
def academy_class(db, course, teacher_user):
    cls = AcademyClassModel(
        course_id=course.id,
        title="Test Class",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 11, 30),
        capacity=25,
        tuition=500000,
        num_sessions=5,
        status="ACTIVE",
        teacher_user_id=teacher_user.id,
    )
    db.session.add(cls)
    db.session.commit()
    return cls


@pytest.fixture
def enrollment(db, student_user, academy_class):
    from datetime import datetime as _dt

    e = EnrollmentModel(
        student_user_id=student_user.id,
        class_id=academy_class.id,
        status="APPROVED",
        requested_at=_dt(2026, 8, 25),
        approved_at=_dt(2026, 8, 26),
    )
    db.session.add(e)
    db.session.commit()
    return e


@pytest.fixture
def assessment(db, academy_class, teacher_user):
    a = AssessmentModel(
        class_id=academy_class.id,
        type="MIDTERM",
        title="Midterm Exam",
        max_score=Decimal("20"),
        passing_score=Decimal("10"),
        status="SCHEDULED",
        created_by=teacher_user.id,
    )
    db.session.add(a)
    db.session.commit()
    return a


# ---------------------------------------------------------------------------
# Audit Service Tests
# ---------------------------------------------------------------------------


class TestAuditService:
    def test_log_creates_record(self, db, admin_user):
        from app.application.audit.audit_service import log

        entry = log(
            user_id=admin_user.id,
            action="UPDATE",
            entity_type="ASSESSMENT_RESULT",
            entity_id=1,
            old_values={"score": 10.0},
            new_values={"score": 15.0},
        )
        db.session.commit()

        assert entry.id is not None
        assert entry.action == "UPDATE"
        assert entry.entity_type == "ASSESSMENT_RESULT"
        assert entry.entity_id == 1
        assert entry.old_values == {"score": 10.0}
        assert entry.new_values == {"score": 15.0}
        assert entry.user_id == admin_user.id

    def test_log_serializes_decimals(self, db, admin_user):
        from app.application.audit.audit_service import log

        entry = log(
            user_id=admin_user.id,
            action="CORRECT",
            entity_type="FINANCIAL_TRANSACTION",
            entity_id=5,
            old_values={"amount": Decimal("100.50")},
            new_values={"amount": Decimal("200.00")},
        )
        db.session.commit()

        assert entry.old_values["amount"] == 100.5
        assert entry.new_values["amount"] == 200.0

    def test_log_serializes_dates(self, db, admin_user):
        from app.application.audit.audit_service import log

        now = datetime(2026, 9, 1, 12, 0, 0)
        entry = log(
            user_id=admin_user.id,
            action="CREATE",
            entity_type="SESSION",
            entity_id=1,
            new_values={"scheduled_date": date(2026, 9, 5), "timestamp": now},
        )
        db.session.commit()

        assert entry.new_values["scheduled_date"] == "2026-09-05"
        assert entry.new_values["timestamp"] == "2026-09-01T12:00:00"

    def test_get_audit_logs_filters(self, db, admin_user):
        from app.application.audit.audit_service import get_audit_logs, log

        log(
            user_id=admin_user.id,
            action="UPDATE",
            entity_type="ASSESSMENT_RESULT",
            entity_id=1,
        )
        log(
            user_id=admin_user.id,
            action="CORRECT",
            entity_type="FINANCIAL_TRANSACTION",
            entity_id=2,
        )
        log(
            user_id=admin_user.id,
            action="UPDATE",
            entity_type="FINANCIAL_TRANSACTION",
            entity_id=3,
        )
        db.session.commit()

        # Filter by entity_type
        results = get_audit_logs(entity_type="ASSESSMENT_RESULT")
        assert len(results) == 1
        assert results[0].entity_id == 1

        # Filter by action
        results = get_audit_logs(action="CORRECT")
        assert len(results) == 1
        assert results[0].entity_id == 2

        # Filter by both
        results = get_audit_logs(entity_type="FINANCIAL_TRANSACTION", action="UPDATE")
        assert len(results) == 1
        assert results[0].entity_id == 3

    def test_count_audit_logs(self, db, admin_user):
        from app.application.audit.audit_service import count_audit_logs, log

        log(
            user_id=admin_user.id,
            action="UPDATE",
            entity_type="ASSESSMENT_RESULT",
            entity_id=1,
        )
        log(
            user_id=admin_user.id,
            action="UPDATE",
            entity_type="ASSESSMENT_RESULT",
            entity_id=2,
        )
        db.session.commit()

        assert count_audit_logs() == 2
        assert count_audit_logs(entity_type="ASSESSMENT_RESULT") == 2
        assert count_audit_logs(action="DELETE") == 0


# ---------------------------------------------------------------------------
# Assessment Audit Integration Tests
# ---------------------------------------------------------------------------


class TestAssessmentAuditLogging:
    def test_grade_update_creates_audit_log(
        self, db, admin_user, enrollment, assessment
    ):
        """Recording a grade on an existing graded result should create an audit log."""
        from app.application.assessment import assessment_service

        # First grading
        result = assessment_service.record_result(
            assessment.id,
            enrollment.id,
            score=15.0,
            graded_by=admin_user.id,
        )
        db.session.commit()

        # Second grading (update) - should trigger audit log
        assessment_service.record_result(
            assessment.id,
            enrollment.id,
            score=18.0,
            graded_by=admin_user.id,
        )
        db.session.commit()

        logs = AuditLogModel.query.filter_by(
            entity_type="ASSESSMENT_RESULT",
            entity_id=result.id,
        ).all()

        # Should have at least one audit log for the update
        assert len(logs) >= 1
        log_entry = logs[-1]
        assert log_entry.action == "UPDATE"
        assert log_entry.user_id == admin_user.id
        assert log_entry.old_values is not None
        assert log_entry.new_values is not None
        assert log_entry.old_values["score"] == 15.0
        assert log_entry.new_values["score"] == 18.0

    def test_update_result_creates_audit_log(
        self, db, admin_user, enrollment, assessment
    ):
        """update_result should create an audit log."""
        from app.application.assessment import assessment_service

        # First grading
        result = assessment_service.record_result(
            assessment.id,
            enrollment.id,
            score=12.0,
            graded_by=admin_user.id,
        )
        db.session.commit()

        # Update via update_result
        assessment_service.update_result(
            result.id,
            score=16.0,
            graded_by=admin_user.id,
        )
        db.session.commit()

        logs = AuditLogModel.query.filter_by(
            entity_type="ASSESSMENT_RESULT",
            entity_id=result.id,
            action="UPDATE",
        ).all()

        assert len(logs) >= 1
        log_entry = logs[-1]
        assert log_entry.user_id == admin_user.id
        assert log_entry.old_values["score"] == 12.0
        assert log_entry.new_values["score"] == 16.0

    def test_no_audit_log_on_first_grading(
        self, db, admin_user, enrollment, assessment
    ):
        """First grading (not a correction) should not create an audit log."""
        from app.application.assessment import assessment_service

        result = assessment_service.record_result(
            assessment.id,
            enrollment.id,
            score=15.0,
            graded_by=admin_user.id,
        )
        db.session.commit()

        logs = AuditLogModel.query.filter_by(
            entity_type="ASSESSMENT_RESULT",
            entity_id=result.id,
        ).all()

        # No audit log for first grading (it was a new result, not a correction)
        assert len(logs) == 0


# ---------------------------------------------------------------------------
# Finance Audit Integration Tests
# ---------------------------------------------------------------------------


class TestFinanceAuditLogging:
    def test_correct_transaction_creates_audit_log(self, db, admin_user, student_user):
        from app.application.finance import finance_service

        # Create a charge
        charge = finance_service.create_charge(
            student_user_id=student_user.id,
            amount=Decimal("500000"),
            category="TUITION",
            description="Tuition fee",
            created_by=admin_user.id,
        )
        db.session.commit()

        # Correct the transaction
        finance_service.correct_transaction(
            charge.id,
            new_amount=Decimal("450000"),
            new_description="Corrected tuition",
            corrected_by=admin_user.id,
        )
        db.session.commit()

        logs = AuditLogModel.query.filter_by(
            entity_type="FINANCIAL_TRANSACTION",
            entity_id=charge.id,
            action="CORRECT",
        ).all()

        assert len(logs) == 1
        log_entry = logs[0]
        assert log_entry.user_id == admin_user.id
        assert log_entry.old_values["amount"] == "500000.00"
        assert Decimal(log_entry.new_values["amount"]) == Decimal("450000")
        assert log_entry.old_values["description"] == "Tuition fee"
        assert log_entry.new_values["description"] == "Corrected tuition"

    def test_reverse_transaction_creates_audit_log(self, db, admin_user, student_user):
        from app.application.finance import finance_service

        # Create a charge
        charge = finance_service.create_charge(
            student_user_id=student_user.id,
            amount=Decimal("500000"),
            category="TUITION",
            description="Tuition fee",
            created_by=admin_user.id,
        )
        db.session.commit()

        # Reverse the transaction
        finance_service.reverse_transaction(
            charge.id,
            description="Student cancelled",
            reversed_by=admin_user.id,
        )
        db.session.commit()

        logs = AuditLogModel.query.filter_by(
            entity_type="FINANCIAL_TRANSACTION",
            entity_id=charge.id,
            action="REVERSE",
        ).all()

        assert len(logs) == 1
        log_entry = logs[0]
        assert log_entry.user_id == admin_user.id
        assert log_entry.old_values["amount"] == "500000.00"
        assert log_entry.new_values["transaction_type"] == "REVERSAL"
        assert (
            Decimal(log_entry.new_values["amount"]) > 0
        )  # Reversal of CHARGE is positive


# ---------------------------------------------------------------------------
# Scheduler Tests
# ---------------------------------------------------------------------------


def _sunday():
    """Freeze app.scheduler.date on Sunday 2026-03-08 (a Sunday).

    Payment reminders run on Sundays; pinning the weekday keeps cadence
    tests deterministic regardless of the wall-clock date.
    """

    class _SundayDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 3, 8)

    return patch("app.scheduler.date", _SundayDate)


class TestScheduler:
    def test_session_reminder_sends_notifications(
        self, db, student_user, academy_class, enrollment
    ):
        from app.application.notification.notification_service import (
            get_user_in_app_notifications,
        )
        from app.scheduler import _daily_class_reminder_job

        # Create a session scheduled for tomorrow
        tomorrow = date.today() + timedelta(days=1)
        session = SessionModel(
            class_id=academy_class.id,
            session_number=1,
            scheduled_date=tomorrow,
            start_time=time(10, 0),
            end_time=time(12, 0),
            status="SCHEDULED",
            title="Session 1",
        )
        db.session.add(session)
        db.session.commit()

        # Run the job
        _daily_class_reminder_job()

        # Check that in-app notifications were created
        notifications = get_user_in_app_notifications(student_user.id)
        assert len(notifications) >= 1
        reminder = notifications[0]
        assert "یادآوری" in reminder.title
        assert academy_class.title in reminder.message

    def test_no_reminders_when_no_sessions(self, db, student_user, academy_class):
        from app.application.notification.notification_service import (
            get_user_in_app_notifications,
        )
        from app.scheduler import _daily_class_reminder_job

        # No sessions for tomorrow
        _daily_class_reminder_job()

        notifications = get_user_in_app_notifications(student_user.id)
        assert len(notifications) == 0

    def test_payment_reminder_sends_notifications(self, db, student_user):
        from app.application.notification.notification_service import (
            get_user_in_app_notifications,
        )
        from app.scheduler import _weekly_payment_reminder_job

        # Create a charge (debt)
        charge = FinancialTransactionModel(
            student_user_id=student_user.id,
            amount=Decimal("500000"),
            transaction_type="CHARGE",
            category="TUITION",
            description="Tuition",
            status="ACTIVE",
        )
        db.session.add(charge)
        db.session.commit()

        # Run the job (payment reminders run on Sundays)
        with _sunday():
            _weekly_payment_reminder_job()

        notifications = get_user_in_app_notifications(student_user.id)
        assert len(notifications) >= 1
        reminder = notifications[0]
        assert "بدهی" in reminder.message or "پرداخت" in reminder.message

    def test_no_payment_reminder_when_no_debt(self, db, student_user):
        from app.application.notification.notification_service import (
            get_user_in_app_notifications,
        )
        from app.scheduler import _weekly_payment_reminder_job

        # No debt
        _weekly_payment_reminder_job()
        notifications = get_user_in_app_notifications(student_user.id)
        assert len(notifications) == 0

    def test_daily_reminder_is_idempotent_across_runs(
        self, db, student_user, academy_class, enrollment
    ):
        """Repeated/overlapping runs (e.g. N Gunicorn workers) send once."""
        from app.application.notification.notification_service import (
            get_user_in_app_notifications,
        )
        from app.scheduler import _daily_class_reminder_job

        tomorrow = date.today() + timedelta(days=1)
        session = SessionModel(
            class_id=academy_class.id,
            session_number=1,
            scheduled_date=tomorrow,
            start_time=time(10, 0),
            end_time=time(12, 0),
            status="SCHEDULED",
            title="Session 1",
        )
        db.session.add(session)
        db.session.commit()

        _daily_class_reminder_job()
        _daily_class_reminder_job()

        notifications = get_user_in_app_notifications(student_user.id)
        assert len(notifications) == 1

    def test_weekly_reminder_is_idempotent_across_runs(self, db, student_user):
        from app.application.notification.notification_service import (
            get_user_in_app_notifications,
        )
        from app.scheduler import _weekly_payment_reminder_job

        charge = FinancialTransactionModel(
            student_user_id=student_user.id,
            amount=Decimal("500000"),
            transaction_type="CHARGE",
            category="TUITION",
            description="Tuition",
            status="ACTIVE",
        )
        db.session.add(charge)
        db.session.commit()

        with _sunday():
            _weekly_payment_reminder_job()
            _weekly_payment_reminder_job()

        notifications = get_user_in_app_notifications(student_user.id)
        assert len(notifications) == 1

    def test_run_jobs_now(self, db, admin_user, student_user, academy_class):
        from app.scheduler import run_jobs_now

        tomorrow = date.today() + timedelta(days=1)
        session = SessionModel(
            class_id=academy_class.id,
            session_number=1,
            scheduled_date=tomorrow,
            start_time=time(10, 0),
            end_time=time(12, 0),
            status="SCHEDULED",
            title="Session 1",
        )
        db.session.add(session)
        db.session.commit()

        results = run_jobs_now()
        assert results["class_reminder"] == "ok"
        assert results["payment_reminder"] == "ok"


# ---------------------------------------------------------------------------
# Admin Audit Log Route Tests
# ---------------------------------------------------------------------------


class TestAdminAuditLogRoute:
    def test_audit_logs_requires_admin(self, db, client, student_user):
        """Non-admin users should be redirected."""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(student_user.id)
            sess["_fresh"] = True

        resp = client.get("/admin/audit-logs")
        assert resp.status_code in (302, 403)

    def test_audit_logs_page_loads(self, db, client, admin_user):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)
            sess["_fresh"] = True

        resp = client.get("/admin/audit-logs")
        assert resp.status_code == 200
        assert "گزارش تغییرات" in resp.data.decode("utf-8")

    def test_audit_logs_filter(self, db, client, admin_user):
        from app.application.audit.audit_service import log

        log(
            user_id=admin_user.id,
            action="UPDATE",
            entity_type="ASSESSMENT_RESULT",
            entity_id=1,
        )
        log(
            user_id=admin_user.id,
            action="CORRECT",
            entity_type="FINANCIAL_TRANSACTION",
            entity_id=2,
        )
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)
            sess["_fresh"] = True

        resp = client.get("/admin/audit-logs?entity_type=ASSESSMENT_RESULT")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert "ASSESSMENT_RESULT" in body
