"""Tests for the administrator dashboard (portal admin).

Covers metric correctness (role/status/distinct-entity semantics), monthly
trend definitions, attendance rules, links/filters, empty/error states,
whole-card anchor DOM, and query-count regression.
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
    capacity: int = 30,
) -> AcademyClassModel:
    cls = AcademyClassModel(
        course_id=course.id,
        title=title,
        start_date=start_date or date.today(),
        capacity=capacity,
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
    def test_running_vs_planned_classes(self, db, admin):
        course = make_course()
        make_class(course, "Running", status="ACTIVE")
        make_class(course, "Planned", status="PLANNED")
        make_class(course, "Done", status="COMPLETED")
        make_class(course, "Dropped", status="CANCELLED")

        data = portal_service.get_admin_dashboard()
        assert data["running_classes"] == 1
        assert data["planned_classes"] == 1

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

    def test_class_list_status_filter(self, client, db):
        make_user("cl_admin", "ADMIN")
        course = make_course()
        make_class(course, "R1", status="ACTIVE")
        make_class(course, "P1", status="PLANNED")

        login_as(client, "cl_admin")
        response = client.get("/academy/classes?status=ACTIVE")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "R1" in body
        assert "P1" not in body


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
    def test_open_and_closed_counted_separately(self, db, admin):
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
        assert data["open_assessments"] == 1
        assert data["closed_assessments"] == 1
        endpoints = [
            (i["endpoint"], i.get("endpoint_args"))
            for i in data["attention_items"]
            if i["endpoint"] == "assessment.admin_assessment_list"
        ]
        assert ("assessment.admin_assessment_list", {"status": "OPEN"}) in endpoints
        assert ("assessment.admin_assessment_list", {"status": "CLOSED"}) in endpoints


class TestFinanceMetrics:
    def test_month_gross_counts_only_active_payments(self, db, admin):
        student = make_user("fs1", "STUDENT")
        finance_service.record_payment(
            student.id, Decimal("1000"), payment_method="CASH"
        )
        finance_service.record_payment(
            student.id, Decimal("500"), payment_method="CASH"
        )
        # A corrected payment counts once, at its corrected amount.
        tx = finance_service.record_payment(
            student.id, Decimal("9999"), payment_method="CASH"
        )
        finance_service.correct_transaction(tx.id, new_amount=Decimal("100"))
        finance_service.create_charge(student.id, Decimal("3000"), category="TUITION")

        data = portal_service.get_admin_dashboard()
        assert Decimal(str(data["finance_summary"]["month_payments"])) == Decimal(
            "1600"
        )
        assert Decimal(str(data["finance_summary"]["billed_tuition"])) == Decimal(
            "3000"
        )

    def test_monthly_buckets_match_per_month_reports(self, db, admin):
        """Canonical grouped buckets equal month-by-month get_revenue_report()."""
        student = make_user("fsb", "STUDENT")
        payment = finance_service.record_payment(
            student.id, Decimal("2000"), payment_method="CASH"
        )
        finance_service.record_refund(
            student.id, Decimal("500"), related_transaction_id=payment.id
        )

        today = date.today()
        first = today.replace(day=1)
        expected = finance_service.get_revenue_report(start_date=first)
        buckets = finance_service.get_monthly_revenue(first, 1)
        assert len(buckets) == 1
        assert buckets[0]["gross"] == expected["payments"]
        assert buckets[0]["refunds"] == expected["refunds"]
        assert buckets[0]["net"] == expected["net_revenue"]

    def test_monthly_revenue_reversal_attribution(self, db, admin):
        student = make_user("fsr", "STUDENT")
        payment = finance_service.record_payment(
            student.id, Decimal("3000"), payment_method="CASH"
        )
        finance_service.reverse_transaction(payment.id, description="oops")

        today = date.today()
        buckets = finance_service.get_monthly_revenue(today.replace(day=1), 1)
        # Reversals carry signed amounts: reversing a +3000 payment yields -3000.
        assert buckets[0]["gross"] == Decimal("3000")
        assert buckets[0]["net"] == Decimal("0")

    def test_monthly_revenue_old_month_bucket(self, db, admin):
        student = make_user("fso", "STUDENT")
        tx = finance_service.record_payment(
            student.id, Decimal("4000"), payment_method="CASH"
        )
        first_of_month = date.today().replace(day=1)
        prev = (first_of_month - timedelta(days=1)).replace(day=1)
        tx.created_at = datetime.combine(prev + timedelta(days=10), datetime.min.time())
        _db.session.commit()

        buckets = finance_service.get_monthly_revenue(prev, 2)
        assert buckets[0]["gross"] == Decimal("4000")  # previous month
        assert buckets[1]["gross"] == Decimal("0")  # current month

    def test_non_active_transactions_excluded_from_collections(self, db, admin):
        from app.infrastructure.database.models import FinancialTransactionModel

        student = make_user("fs4", "STUDENT")
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
        assert overview["sessions"][0]["needs_attention"] is True
        assert overview["sessions"][0]["eligible_count"] == 2
        assert overview["sessions"][0]["recorded_count"] == 1
        assert overview["completion_rate"] == 0
        assert overview["sessions"][0]["fill_percent"] > 0

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
        assert not [
            i
            for i in data["attention_items"]
            if i["endpoint"] == "attendance.admin_attendance_list"
        ]

    def test_capacity_watch_flags_near_full_classes(self, db, admin):
        course = make_course()
        full = make_class(course, "Almost Full", status="ACTIVE", capacity=10)
        for i in range(9):
            make_enrollment(make_user(f"cap{i}", "STUDENT"), full, "APPROVED")
        roomy = make_class(course, "Roomy", status="ACTIVE", capacity=10)
        make_enrollment(make_user("capx", "STUDENT"), roomy, "APPROVED")

        data = portal_service.get_admin_dashboard()
        assert data["capacity_watch"] is not None
        assert len(data["capacity_watch"]) == 1
        assert data["capacity_watch"][0]["title"] == "Almost Full"
        assert data["capacity_watch"][0]["fill_percent"] == 90
        assert any(
            i["endpoint"] == "academy.class_detail" for i in data["attention_items"]
        )


class TestAttendanceWeek:
    def test_weekly_rates_and_neutral_days(self, db, admin):
        course = make_course()
        cls = make_class(course, start_date=date.today() - timedelta(days=6))
        s1 = make_user("ws1", "STUDENT")
        e1 = make_enrollment(s1, cls)
        recorded_day = date.today() - timedelta(days=1)
        make_session(cls, recorded_day, number=1)
        sess = SessionModel.query.filter_by(
            class_id=cls.id, scheduled_date=recorded_day
        ).first()
        _db.session.add(
            AttendanceModel(enrollment_id=e1.id, session_id=sess.id, status="PRESENT")
        )
        make_session(cls, date.today() - timedelta(days=3), number=2)
        _db.session.commit()

        data = portal_service.get_admin_dashboard()
        week = data["attendance_chart"]["points"]
        assert week is not None
        assert len(week) == 7
        by_key = {d["key"]: d for d in week}
        assert by_key[recorded_day.isoformat()]["rate"] == 1.0
        missing = by_key[(date.today() - timedelta(days=3)).isoformat()]
        assert missing["rate"] == 0
        empty = by_key[(date.today() - timedelta(days=5)).isoformat()]
        assert empty["rate"] is None
        assert data["attendance_chart"]["y_max"] == 100.0


class TestChartModels:
    def test_collections_chart_nice_scale_and_labels(self, db, admin):
        student = make_user("ch1", "STUDENT")
        finance_service.record_payment(
            student.id, Decimal("4500000"), payment_method="CASH"
        )

        data = portal_service.get_admin_dashboard()
        chart = data["collections_chart"]
        assert chart is not None
        assert len(chart["points"]) == 12
        assert chart["points"][-1]["gross"] == Decimal("4500000")
        assert chart["points"][-1]["label"]
        assert chart["y_max"] >= 4500000
        assert len(chart["ticks"]) == 5
        assert chart["ticks"][0] == 0

    def test_enrollments_chart_requests_and_approvals(self, db, admin):
        course = make_course()
        cls = make_class(course)
        s1 = make_user("ce1", "STUDENT")
        s2 = make_user("ce2", "STUDENT")
        make_enrollment(s1, cls, "APPROVED")
        make_enrollment(s2, cls, "PENDING")

        data = portal_service.get_admin_dashboard()
        chart = data["enrollments_chart"]
        assert chart is not None
        assert len(chart["points"]) == 12
        current = chart["points"][-1]
        assert current["requested"] == 2
        assert current["approved"] == 1


# ---------------------------------------------------------------------------
# Query-count regression
# ---------------------------------------------------------------------------


class TestQueryBudget:
    def test_dashboard_query_count_is_bounded(self, db, admin):
        from sqlalchemy import event

        from app.extensions import db as _db_ext

        course = make_course()
        for i in range(3):
            cls = make_class(course, f"QC{i}")
            for n in range(4):
                make_enrollment(make_user(f"qc{i}_{n}", "STUDENT"), cls, "APPROVED")
            make_session(cls, date.today(), number=1)

        count = [0]

        @event.listens_for(_db_ext.engine, "before_cursor_execute")
        def _count(conn, cursor, statement, params, context, executemany):
            count[0] += 1

        try:
            portal_service.get_admin_dashboard()
        finally:
            event.remove(_db_ext.engine, "before_cursor_execute", _count)

        # Grouped aggregates keep the service well under the historical 66–77
        # range even with several classes, sessions, and enrollments.
        assert count[0] < 60, f"dashboard issued {count[0]} queries"


# ---------------------------------------------------------------------------
# Links, authorization, and card anchors
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
            "/academy/classes?status=ACTIVE",
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
            "/assessment/admin/all?status=OPEN",
            "/assessment/admin/all?status=CLOSED",
            "/reporting/admin/overview",
            "/admin/audit-logs",
        ]
        for url in urls:
            response = client.get(url)
            assert response.status_code == 200, f"dashboard link broken: {url}"

    def test_kpi_cards_are_single_anchors_with_exact_destinations(self, client, admin):
        """Each KPI card is one <a> (no nested links) pointing at its module."""
        from bs4 import BeautifulSoup

        login_as(client, "dash_admin")
        response = client.get("/portal/admin")
        assert response.status_code == 200
        soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")
        cards = soup.select("a.stat-card-link")
        assert len(cards) == 8
        hrefs = {card["href"] for card in cards}
        assert "/admin/users?role=STUDENT" in hrefs
        assert "/admin/users?role=TEACHER" in hrefs
        assert "/academy/classes?status=ACTIVE" in hrefs
        assert "/academy/courses" in hrefs
        assert "/enrollment/admin/all?status=APPROVED" in hrefs
        assert "/enrollment/admin/pending" in hrefs
        assert "/finance/admin/dashboard" in hrefs
        assert "/finance/admin/reports/debt" in hrefs
        for card in cards:
            # No nested interactive elements inside the card link.
            assert not card.select("a"), "nested link inside KPI card"
            assert not card.select("button"), "button inside KPI card"
            assert card.get("aria-label"), "KPI card missing accessible name"
            assert card.select_one(".stat-card-value") is not None

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
# Empty and error states
# ---------------------------------------------------------------------------


class TestEmptyAcademy:
    def test_empty_academy_renders_onboarding(self, client, admin):
        login_as(client, "dash_admin")
        response = client.get("/portal/admin")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "هنوز دانش‌آموز یا کلاس فعالی ثبت نشده است" in body
        assert "درخواست در انتظاری وجود ندارد" in body
        assert "امروز جلسه‌ای برنامه‌ریزی نشده است" in body

        data = portal_service.get_admin_dashboard()
        assert data["active_students"] == 0
        assert data["active_teachers"] == 0
        assert data["running_classes"] == 0
        assert data["distinct_courses"] == 0
        assert data["top_debtors"] == []
        assert data["today_overview"]["completion_rate"] is None
        assert len(data["collections_chart"]["points"]) == 12
        assert len(data["attendance_chart"]["points"]) == 7

    def test_optional_section_failure_renders_error_state(
        self, client, admin, monkeypatch
    ):
        import app.application.portal.portal_service as service

        def boom():
            raise RuntimeError("trend DB outage")

        monkeypatch.setattr(service, "_get_monthly_revenue", boom)
        login_as(client, "dash_admin")
        response = client.get("/portal/admin")
        assert response.status_code == 200
        assert "روند وصول با خطا مواجه شد" in response.get_data(as_text=True)
        # The month KPI falls back to direct canonical calls (never blank).
        assert "وصول خالص این ماه" in response.get_data(as_text=True)
