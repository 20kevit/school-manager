"""Tests for the administrator dashboard (portal admin).

Covers metric correctness (role/status/distinct-course semantics), date and
financial boundaries, links/authorization, and empty/error states.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest

from app.application.finance import finance_service
from app.application.portal import portal_service
from app.extensions import db as _db
from app.infrastructure.database.models import (
    AcademyClassModel,
    AssessmentModel,
    AttendanceModel,
    CourseModel,
    EnrollmentModel,
    RoleModel,
    SessionModel,
    StudentProfileModel,
    TeacherProfileModel,
    UserModel,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_role(name: str) -> RoleModel:
    role = RoleModel.query.filter_by(name=name).first()
    if role is None:
        role = RoleModel(name=name)
        _db.session.add(role)
        _db.session.flush()
    return role


def make_user(
    login: str,
    role: str,
    *,
    active: bool = True,
    password: str = "pass12345",
    created_at: datetime | None = None,
) -> UserModel:
    user = UserModel(login=login, is_active_user=active)
    user.set_password(password)
    user.roles.append(_get_role(role))
    _db.session.add(user)
    _db.session.flush()
    if created_at is not None:
        user.created_at = created_at
    if role == "STUDENT":
        _db.session.add(
            StudentProfileModel(
                user_id=user.id,
                first_name="Test",
                last_name=f"Student-{login}",
                national_id=f"{abs(hash(login)) % 10**10:010d}",
                mobile_phone="09120000000",
                birth_date=date(2000, 1, 1),
                gender="MALE",
            )
        )
    elif role == "TEACHER":
        _db.session.add(
            TeacherProfileModel(
                user_id=user.id,
                first_name="Test",
                last_name=f"Teacher-{login}",
                national_id=f"{abs(hash(login)) % 10**10:010d}",
                mobile_phone="09120000000",
            )
        )
    _db.session.commit()
    return user


def make_course(title: str = "Math") -> CourseModel:
    course = CourseModel(title=title, num_sessions=8)
    _db.session.add(course)
    _db.session.commit()
    return course


def make_class(
    course: CourseModel,
    title: str = "Class A",
    *,
    status: str = "ACTIVE",
    start_date: date | None = None,
    tuition: Decimal = Decimal("1000000"),
) -> AcademyClassModel:
    cls = AcademyClassModel(
        course_id=course.id,
        title=title,
        start_date=start_date or date.today(),
        capacity=30,
        tuition=tuition,
        num_sessions=8,
        status=status,
    )
    _db.session.add(cls)
    _db.session.commit()
    return cls


def make_enrollment(
    student: UserModel,
    cls: AcademyClassModel,
    status: str = "APPROVED",
) -> EnrollmentModel:
    now = datetime.now()
    enrollment = EnrollmentModel(
        student_user_id=student.id,
        class_id=cls.id,
        status=status,
        requested_at=now,
        approved_at=now if status == "APPROVED" else None,
    )
    _db.session.add(enrollment)
    _db.session.commit()
    return enrollment


def make_session(cls: AcademyClassModel, day: date, number: int = 1) -> SessionModel:
    session = SessionModel(
        class_id=cls.id,
        session_number=number,
        scheduled_date=day,
        start_time=time(10, 0),
        end_time=time(11, 30),
        status="SCHEDULED",
    )
    _db.session.add(session)
    _db.session.commit()
    return session


def login_as(client, login: str, password: str = "pass12345"):
    return client.post("/auth/login", data={"login": login, "password": password})


@pytest.fixture
def admin(db):
    return make_user("dash_admin", "ADMIN")


# ---------------------------------------------------------------------------
# A. Metric correctness
# ---------------------------------------------------------------------------


class TestRoleCounts:
    def test_students_count_is_role_specific(self, db, admin):
        make_user("s1", "STUDENT")
        make_user("s2", "STUDENT")
        make_user("s_inactive", "STUDENT", active=False)
        make_user("t1", "TEACHER")
        make_user("a2", "ADMIN")

        data = portal_service.get_admin_dashboard()
        assert data["active_students"] == 2
        assert data["active_teachers"] == 1

    def test_teachers_exclude_inactive_and_other_roles(self, db, admin):
        make_user("t1", "TEACHER")
        make_user("t_off", "TEACHER", active=False)
        make_user("s1", "STUDENT")

        data = portal_service.get_admin_dashboard()
        assert data["active_teachers"] == 1

    def test_new_students_use_30_day_window(self, db, admin):
        make_user("fresh", "STUDENT")
        make_user(
            "old",
            "STUDENT",
            created_at=datetime.now() - timedelta(days=60),
        )
        make_user(
            "old_inactive",
            "STUDENT",
            active=False,
            created_at=datetime.now() - timedelta(days=60),
        )

        data = portal_service.get_admin_dashboard()
        assert data["new_students"] == 1


class TestClassAndCourseCounts:
    def test_active_classes_exclude_completed_and_cancelled(self, db, admin):
        course = make_course()
        make_class(course, "Running", status="ACTIVE")
        make_class(course, "Planned", status="PLANNED")
        make_class(course, "Done", status="COMPLETED")
        make_class(course, "Dropped", status="CANCELLED")

        data = portal_service.get_admin_dashboard()
        assert data["active_classes"] == 2

    def test_upcoming_classes_are_future_operational(self, db, admin):
        course = make_course()
        make_class(
            course,
            "Future",
            status="PLANNED",
            start_date=date.today() + timedelta(days=10),
        )
        make_class(course, "Now", status="ACTIVE", start_date=date.today())
        make_class(
            course,
            "Future-cancelled",
            status="CANCELLED",
            start_date=date.today() + timedelta(days=10),
        )

        data = portal_service.get_admin_dashboard()
        assert data["upcoming_classes"] == 1

    def test_courses_count_distinct_courses_not_classes(self, db, admin):
        c1 = make_course("Math")
        c2 = make_course("Physics")
        make_class(c1, "Math 1")
        make_class(c1, "Math 2")
        make_class(c2, "Physics 1")

        data = portal_service.get_admin_dashboard()
        assert data["distinct_courses"] == 2


class TestEnrollmentMetrics:
    def test_enrollment_statuses_and_unique_students(self, db, admin):
        course = make_course()
        cls = make_class(course)
        cls2 = make_class(course, "Class B")
        s1 = make_user("es1", "STUDENT")
        s2 = make_user("es2", "STUDENT")
        make_enrollment(s1, cls, "APPROVED")
        make_enrollment(s1, cls2, "APPROVED")  # same student, two enrollments
        make_enrollment(s2, cls, "PENDING")
        rejected = make_enrollment(s2, cls2, "PENDING")
        rejected.status = "REJECTED"
        _db.session.commit()
        cancelled = make_enrollment(make_user("es3", "STUDENT"), cls2, "APPROVED")
        cancelled.status = "CANCELLED"
        _db.session.commit()

        data = portal_service.get_admin_dashboard()
        assert data["approved_enrollments"] == 2
        assert data["pending_enrollments"] == 1
        assert data["approved_students"] == 1


class TestAssessmentMetrics:
    def test_assessment_attention_counts_open_and_closed(self, db, admin):
        course = make_course()
        cls = make_class(course)
        for i, status in enumerate(
            ["DRAFT", "SCHEDULED", "OPEN", "CLOSED", "GRADED", "CANCELLED"]
        ):
            _db.session.add(
                AssessmentModel(
                    class_id=cls.id,
                    type="QUIZ",
                    title=f"Exam {i}",
                    status=status,
                )
            )
        _db.session.commit()

        data = portal_service.get_admin_dashboard()
        assert data["assessments_total"] == 5  # CANCELLED excluded
        assert data["assessments_attention"] == 2  # OPEN + CLOSED


class TestFinanceMetrics:
    def test_month_gross_counts_only_active_payments(self, db, admin):
        student = make_user("fs1", "STUDENT")
        finance_service.record_payment(
            student.id, Decimal("1000"), payment_method="CASH"
        )
        finance_service.record_payment(
            student.id, Decimal("500"), payment_method="CASH"
        )
        # A corrected payment counts once, at its corrected amount: the
        # original becomes CORRECTED (excluded) and the copy is ACTIVE.
        tx = finance_service.record_payment(
            student.id, Decimal("9999"), payment_method="CASH"
        )
        finance_service.correct_transaction(tx.id, new_amount=Decimal("100"))
        # A charge is billed tuition, not collected cash.
        finance_service.create_charge(student.id, Decimal("3000"), category="TUITION")

        data = portal_service.get_admin_dashboard()
        assert Decimal(str(data["finance_summary"]["month_payments"])) == Decimal(
            "1600"
        )
        assert Decimal(str(data["finance_summary"]["billed_tuition"])) == Decimal(
            "3000"
        )

    def test_month_net_subtracts_refunds(self, db, admin):
        student = make_user("fs2", "STUDENT")
        payment = finance_service.record_payment(
            student.id, Decimal("2000"), payment_method="CASH"
        )
        finance_service.record_refund(
            student.id,
            Decimal("500"),
            related_transaction_id=payment.id,
        )

        data = portal_service.get_admin_dashboard()
        assert Decimal(str(data["finance_month"]["current_net"])) == Decimal("1500")
        assert Decimal(str(data["finance_month"]["current_gross"])) == Decimal("2000")

    def test_debt_and_debtors(self, db, admin):
        debtor = make_user("debtor1", "STUDENT")
        finance_service.create_charge(debtor.id, Decimal("1000"), category="TUITION")
        creditor = make_user("creditor1", "STUDENT")
        finance_service.record_payment(
            creditor.id, Decimal("700"), payment_method="CASH"
        )

        data = portal_service.get_admin_dashboard()
        assert data["finance_summary"]["debtors_count"] == 1
        assert Decimal(str(data["finance_summary"]["total_debt"])) == Decimal("1000")
        assert data["top_debtors"] is not None
        assert len(data["top_debtors"]) == 1
        assert data["top_debtors"][0]["student_user_id"] == debtor.id

    def test_old_month_payment_excluded_from_month_kpi(self, db, admin):
        student = make_user("fs3", "STUDENT")
        tx = finance_service.record_payment(
            student.id, Decimal("4000"), payment_method="CASH"
        )
        first_of_month = date.today().replace(day=1)
        tx.created_at = datetime.combine(
            first_of_month - timedelta(days=1), datetime.min.time()
        )
        _db.session.commit()

        data = portal_service.get_admin_dashboard()
        assert Decimal(str(data["finance_summary"]["month_payments"])) == Decimal("0")

    def test_non_active_transactions_excluded_from_collections(self, db, admin):
        from app.infrastructure.database.models import FinancialTransactionModel

        student = make_user("fs4", "STUDENT")
        # A PENDING online payment attempt must not count as collected cash.
        _db.session.add(
            FinancialTransactionModel(
                student_user_id=student.id,
                amount=Decimal("5000"),
                transaction_type="PAYMENT",
                category="OTHER",
                payment_method="ONLINE",
                status="PENDING",
            )
        )
        _db.session.commit()

        data = portal_service.get_admin_dashboard()
        assert Decimal(str(data["finance_summary"]["month_payments"])) == Decimal("0")
        assert Decimal(str(data["finance_month"]["current_net"])) == Decimal("0")


class TestTodayOverview:
    def test_recorded_only_when_all_eligible_have_rows(self, db, admin):
        course = make_course()
        cls = make_class(course, start_date=date.today())
        s1 = make_user("ts1", "STUDENT")
        s2 = make_user("ts2", "STUDENT")
        e1 = make_enrollment(s1, cls)
        make_enrollment(s2, cls)
        session = make_session(cls, date.today())
        _db.session.add(
            AttendanceModel(
                enrollment_id=e1.id, session_id=session.id, status="PRESENT"
            )
        )
        _db.session.commit()

        data = portal_service.get_admin_dashboard()
        overview = data["today_overview"]
        assert overview is not None
        assert overview["total"] == 1
        assert overview["sessions"][0]["is_recorded"] is False
        assert overview["sessions"][0]["eligible_count"] == 2
        assert overview["sessions"][0]["recorded_count"] == 1
        assert overview["completion_rate"] == 0

    def test_cancelled_sessions_excluded(self, db, admin):
        course = make_course()
        cls = make_class(course, start_date=date.today())
        session = make_session(cls, date.today())
        session.status = "CANCELLED"
        _db.session.commit()

        data = portal_service.get_admin_dashboard()
        assert data["today_overview"]["total"] == 0
        assert data["today_overview"]["completion_rate"] is None

    def test_session_without_enrollments_is_neutral(self, db, admin):
        course = make_course()
        cls = make_class(course, start_date=date.today())
        make_session(cls, date.today())

        data = portal_service.get_admin_dashboard()
        overview = data["today_overview"]
        assert overview["total"] == 1
        assert overview["recordable"] == 0
        assert overview["sessions"][0]["needs_attention"] is False
        assert overview["completion_rate"] is None
        # Neutral sessions must not raise an attendance attention item.
        assert not [
            i
            for i in data["attention_items"]
            if i["endpoint"] == "attendance.admin_attendance_list"
        ]


# ---------------------------------------------------------------------------
# C. Links and authorization
# ---------------------------------------------------------------------------


class TestDashboardAccess:
    def test_admin_can_view_dashboard(self, client, admin):
        login_as(client, "dash_admin")
        response = client.get("/portal/admin")
        assert response.status_code == 200
        assert "داشبورد مدیر" in response.get_data(as_text=True)

    def test_unauthenticated_redirects_to_login(self, client, admin):
        response = client.get("/portal/admin", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]

    def test_teacher_cannot_view_admin_dashboard(self, client, db):
        make_user("t_dash", "TEACHER")
        login_as(client, "t_dash")
        response = client.get("/portal/admin", follow_redirects=False)
        assert response.status_code == 403

    def test_student_cannot_view_admin_dashboard(self, client, db):
        make_user("s_dash", "STUDENT")
        login_as(client, "s_dash")
        response = client.get("/portal/admin", follow_redirects=False)
        assert response.status_code == 403

    def test_all_dashboard_destinations_resolve(self, client, admin):
        login_as(client, "dash_admin")
        urls = [
            "/admin/users",
            "/admin/users?role=STUDENT",
            "/admin/users?role=TEACHER",
            "/admin/users/create",
            "/academy/courses",
            "/academy/courses/create",
            "/academy/classes",
            "/academy/classes/create",
            "/enrollment/admin/all",
            "/enrollment/admin/all?status=APPROVED",
            "/enrollment/admin/all?status=PENDING",
            "/enrollment/admin/pending",
            "/enrollment/admin/enroll",
            "/attendance/admin/all",
            "/finance/admin/dashboard",
            "/finance/admin/transactions",
            "/finance/admin/transaction/create",
            "/finance/admin/reports/debt",
            "/assessment/admin/all",
            "/reporting/admin/overview",
            "/admin/audit-logs",
        ]
        for url in urls:
            response = client.get(url)
            assert response.status_code == 200, f"dashboard link broken: {url}"

    def test_enrollment_list_status_filter_matches_kpi(self, client, db):
        make_user("flt_admin", "ADMIN")
        course = make_course()
        cls = make_class(course)
        student = make_user("flt_s", "STUDENT")
        make_enrollment(student, cls, "APPROVED")
        make_enrollment(make_user("flt_s2", "STUDENT"), cls, "PENDING")

        login_as(client, "flt_admin")
        approved = client.get("/enrollment/admin/all?status=APPROVED")
        assert approved.status_code == 200
        approved_body = approved.get_data(as_text=True)
        assert "Student-flt_s" in approved_body
        assert "Student-flt_s2" not in approved_body
        pending = client.get("/enrollment/admin/all?status=PENDING")
        assert pending.status_code == 200
        pending_body = pending.get_data(as_text=True)
        assert "Student-flt_s2" in pending_body

    def test_attention_links_resolve(self, client, db):
        make_user("att_admin", "ADMIN")
        course = make_course()
        cls = make_class(course)
        student = make_user("att_s", "STUDENT")
        make_enrollment(student, cls, "PENDING")
        finance_service.create_charge(student.id, Decimal("100"), category="TUITION")

        login_as(client, "att_admin")
        response = client.get("/portal/admin")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "درخواست ثبت‌نام" in body
        assert "/enrollment/admin/pending" in body
        assert "/finance/admin/reports/debt" in body


# ---------------------------------------------------------------------------
# D. Empty and error states
# ---------------------------------------------------------------------------


class TestEmptyAcademy:
    def test_empty_academy_renders_onboarding(self, client, admin):
        login_as(client, "dash_admin")
        response = client.get("/portal/admin")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        # No broken cards: zeros render, onboarding guidance present.
        assert "هنوز دانش‌آموز یا کلاس فعالی ثبت نشده است" in body
        assert "درخواست در انتظاری وجود ندارد" in body
        assert "امروز جلسه‌ای برنامه‌ریزی نشده است" in body

        data = portal_service.get_admin_dashboard()
        assert data["active_students"] == 0
        assert data["active_teachers"] == 0
        assert data["active_classes"] == 0
        assert data["distinct_courses"] == 0
        assert data["top_debtors"] == []
        assert data["today_overview"]["completion_rate"] is None

    def test_optional_section_failure_renders_error_state(
        self, client, admin, monkeypatch
    ):
        import app.application.portal.portal_service as service

        real_trend = service._get_collection_trend

        def boom():
            raise RuntimeError("trend DB outage")

        monkeypatch.setattr(service, "_get_collection_trend", boom)
        login_as(client, "dash_admin")
        response = client.get("/portal/admin")
        assert response.status_code == 200
        assert "روند وصول با خطا مواجه شد" in response.get_data(as_text=True)
        monkeypatch.setattr(service, "_get_collection_trend", real_trend)
