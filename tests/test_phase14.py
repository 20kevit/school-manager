"""Tests for Phase 14 — Calendar, User Profiles & MVP Data UX."""

from datetime import date, time

import pytest

from app.utils.date_utils import (
    compute_age,
    format_jalali,
    format_jalali_date_input,
    format_jalali_datetime,
    format_jalali_time,
    gregorian_to_jalali,
    jalali_to_gregorian,
    parse_jalali_date,
    parse_jalali_date_or_none,
    parse_jalali_datetime,
)

# ---------------------------------------------------------------------------
# Part 2 — Centralized Persian Date System
# ---------------------------------------------------------------------------


class TestJalaliConversion:
    """Tests for Gregorian <-> Jalali conversion."""

    def test_gregorian_to_jalali_date(self):
        d = date(2026, 9, 23)
        jd = gregorian_to_jalali(d)
        assert jd is not None
        assert jd.year == 1405
        assert jd.month == 7
        assert jd.day == 1

    def test_gregorian_to_jalali_none(self):
        assert gregorian_to_jalali(None) is None

    def test_jalali_to_gregorian_date(self):
        import jdatetime

        jd = jdatetime.date(1405, 7, 1)
        d = jalali_to_gregorian(jd)
        assert d is not None
        assert d.year == 2026
        assert d.month == 9
        assert d.day == 23

    def test_jalali_to_gregorian_none(self):
        assert jalali_to_gregorian(None) is None

    def test_round_trip_date(self):
        original = date(2025, 3, 20)
        jd = gregorian_to_jalali(original)
        result = jalali_to_gregorian(jd)
        assert result == original

    def test_round_trip_datetime(self):
        from datetime import datetime

        original = datetime(2025, 3, 20, 14, 30)
        jd = gregorian_to_jalali(original)
        result = jalali_to_gregorian(jd)
        assert result == original


class TestJalaliFormatting:
    """Tests for Jalali date formatting."""

    def test_format_jalali_default(self):
        d = date(2026, 9, 23)
        result = format_jalali(d)
        assert result == "1405/07/01"

    def test_format_jalali_none(self):
        assert format_jalali(None) == "\u2014"

    def test_format_jalali_custom_format(self):
        d = date(2026, 9, 23)
        result = format_jalali(d, "%Y-%m-%d")
        assert result == "1405-07-01"

    def test_format_jalali_datetime(self):
        from datetime import datetime

        dt = datetime(2026, 9, 23, 14, 30)
        result = format_jalali_datetime(dt)
        assert result == "1405/07/01 14:30"

    def test_format_jalali_datetime_none(self):
        assert format_jalali_datetime(None) == "\u2014"

    def test_format_jalali_time(self):
        t = time(14, 30)
        result = format_jalali_time(t)
        assert result == "14:30"

    def test_format_jalali_time_none(self):
        assert format_jalali_time(None) == "\u2014"

    def test_format_jalali_date_input(self):
        d = date(2026, 9, 23)
        result = format_jalali_date_input(d)
        assert result == "1405/07/01"

    def test_format_jalali_date_input_none(self):
        assert format_jalali_date_input(None) == ""


class TestJalaliParsing:
    """Tests for Jalali date parsing."""

    def test_parse_jalali_date_valid(self):
        result = parse_jalali_date("1405/07/01")
        assert result == date(2026, 9, 23)

    def test_parse_jalali_date_with_dash_separator(self):
        result = parse_jalali_date("1405-07-01")
        assert result == date(2026, 9, 23)

    def test_parse_jalali_date_empty(self):
        with pytest.raises(ValueError, match="\u0627\u0644\u0632\u0627\u0645\u06cc"):
            parse_jalali_date("")

    def test_parse_jalali_date_whitespace(self):
        with pytest.raises(ValueError, match="\u0627\u0644\u0632\u0627\u0645\u06cc"):
            parse_jalali_date("  ")

    def test_parse_jalali_date_invalid_format(self):
        with pytest.raises(ValueError):
            parse_jalali_date("1405/07")

    def test_parse_jalali_date_invalid_jalali_date(self):
        with pytest.raises(ValueError):
            parse_jalali_date("1405/13/01")

    def test_parse_jalali_date_invalid_month(self):
        with pytest.raises(ValueError):
            parse_jalali_date("1405/00/01")

    def test_parse_jalali_date_or_none_valid(self):
        result = parse_jalali_date_or_none("1405/07/01")
        assert result == date(2026, 9, 23)

    def test_parse_jalali_date_or_none_empty(self):
        assert parse_jalali_date_or_none("") is None

    def test_parse_jalali_date_or_none_none(self):
        assert parse_jalali_date_or_none(None) is None

    def test_parse_jalali_datetime_valid(self):
        result = parse_jalali_datetime("1405/07/01 14:30")
        assert result.year == 2026
        assert result.month == 9
        assert result.day == 23
        assert result.hour == 14
        assert result.minute == 30

    def test_parse_jalali_datetime_empty(self):
        with pytest.raises(ValueError, match="\u0627\u0644\u0632\u0627\u0645\u06cc"):
            parse_jalali_datetime("")

    def test_parse_jalali_datetime_invalid_format(self):
        with pytest.raises(ValueError):
            parse_jalali_datetime("1405/07/01")


class TestComputeAge:
    """Tests for age computation."""

    def test_compute_age_past_date(self):
        from datetime import date as date_type

        today = date_type.today()
        birth = date_type(today.year - 20, today.month, today.day)
        assert compute_age(birth) == 20

    def test_compute_age_future_birthday(self):
        from datetime import date as date_type

        today = date_type.today()
        birth = date_type(today.year - 20, today.month + 1, 1)
        assert compute_age(birth) == 19


# ---------------------------------------------------------------------------
# Part 3 — Class Creation/Session Date UX (Jalali in forms)
# ---------------------------------------------------------------------------


class TestClassFormJalali:
    """Tests for class creation with Jalali date inputs."""

    def test_class_create_page_loads(self, client, admin_user):
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
            follow_redirects=False,
        )
        resp = client.get("/academy/classes/create")
        assert resp.status_code == 200
        assert b"jalali-date-input" in resp.data

    def test_class_create_with_jalali_dates(self, client, admin_user, db):
        from app.application.academy.course_service import create_course

        course = create_course(title="Test Course", num_sessions=4)
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
            follow_redirects=False,
        )
        resp = client.post(
            "/academy/classes/create",
            data={
                "title": "Test Class",
                "course_id": str(course.id),
                "start_date": "1405/07/01",
                "capacity": "20",
                "num_sessions": "4",
                "schedule_weekday_0": "SATURDAY",
                "schedule_start_0": "10:00",
                "schedule_end_0": "12:00",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_class_create_with_invalid_jalali_date(self, client, admin_user, db):
        from app.application.academy.course_service import create_course

        course = create_course(title="Test Course", num_sessions=4)
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
            follow_redirects=False,
        )
        resp = client.post(
            "/academy/classes/create",
            data={
                "title": "Test Class",
                "course_id": str(course.id),
                "start_date": "1405/13/01",
                "capacity": "20",
                "num_sessions": "4",
                "schedule_weekday_0": "SATURDAY",
                "schedule_start_0": "10:00",
                "schedule_end_0": "12:00",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Part 4 — Session Editing & History
# ---------------------------------------------------------------------------


class TestSessionEditing:
    """Tests for session editing with history tracking."""

    def _create_class_with_sessions(self, db):
        from app.application.academy.class_service import create_class, get_sessions
        from app.application.academy.course_service import create_course

        course = create_course(title="Edit Course", num_sessions=4)
        cls = create_class(
            course_id=course.id,
            title="Edit Class",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=[
                {
                    "weekday": "MONDAY",
                    "start_time": time(17, 0),
                    "end_time": time(19, 0),
                },
            ],
        )
        sessions = get_sessions(cls.id)
        return cls, sessions

    def test_update_session_date_records_history(self, client, admin_user, db):
        from app.application.academy.class_service import update_session
        from app.infrastructure.database.models import SessionEditHistoryModel

        cls, sessions = self._create_class_with_sessions(db)
        session = sessions[0]
        original_date = session.scheduled_date

        update_session(
            session,
            scheduled_date=date(2026, 10, 1),
            edited_by=admin_user.id,
        )

        history = SessionEditHistoryModel.query.filter_by(session_id=session.id).first()
        assert history is not None
        assert history.previous_date == original_date
        assert history.new_date == date(2026, 10, 1)
        assert history.change_type == "RESCHEDULE"
        assert history.edited_by == admin_user.id

    def test_update_session_time_only(self, client, admin_user, db):
        from app.application.academy.class_service import update_session
        from app.infrastructure.database.models import SessionEditHistoryModel

        cls, sessions = self._create_class_with_sessions(db)
        session = sessions[0]

        update_session(
            session,
            start_time=time(18, 0),
            end_time=time(20, 0),
            edited_by=admin_user.id,
        )

        history = SessionEditHistoryModel.query.filter_by(session_id=session.id).first()
        assert history is not None
        assert history.change_type == "EDIT"
        assert history.new_start_time == time(18, 0)

    def test_update_session_unchanged(self, client, admin_user, db):
        from app.application.academy.class_service import update_session
        from app.infrastructure.database.models import SessionEditHistoryModel

        cls, sessions = self._create_class_with_sessions(db)
        session = sessions[0]

        update_session(
            session,
            title=session.title,
            scheduled_date=session.scheduled_date,
            start_time=session.start_time,
            end_time=session.end_time,
            edited_by=admin_user.id,
        )

        history = SessionEditHistoryModel.query.filter_by(session_id=session.id).count()
        assert history == 0

    def test_update_session_preserves_attendance(self, db, admin_user):
        from app.application.academy.class_service import (
            create_class,
            get_sessions,
            update_session,
        )
        from app.application.academy.course_service import create_course
        from app.application.attendance.attendance_service import record_attendance
        from app.application.enrollment.enrollment_service import admin_enroll_student
        from app.infrastructure.database.models import (
            AttendanceModel,
            RoleModel,
            StudentProfileModel,
            UserModel,
        )

        course = create_course(title="Att Course", num_sessions=4)
        cls = create_class(
            course_id=course.id,
            title="Att Class",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=[
                {
                    "weekday": "MONDAY",
                    "start_time": time(17, 0),
                    "end_time": time(19, 0),
                },
            ],
        )
        sessions = get_sessions(cls.id)

        student = UserModel(login="teststudent")
        student.set_password("pass123")
        role = RoleModel(name="STUDENT")
        db.session.add(role)
        db.session.flush()
        student.roles.append(role)
        db.session.add(student)
        db.session.flush()

        profile = StudentProfileModel(
            user_id=student.id,
            first_name="Test",
            last_name="Student",
            national_id="1111111111",
            mobile_phone="09111111111",
            birth_date=date(2005, 1, 1),
            gender="MALE",
        )
        db.session.add(profile)
        db.session.flush()

        enrollment = admin_enroll_student(student.id, cls.id)

        record_attendance(
            enrollment_id=enrollment.id,
            session_id=sessions[0].id,
            status="PRESENT",
            recorded_by=admin_user.id,
        )

        update_session(
            sessions[0],
            scheduled_date=date(2026, 10, 1),
            edited_by=admin_user.id,
        )

        att = AttendanceModel.query.filter_by(session_id=sessions[0].id).first()
        assert att is not None
        assert att.status == "PRESENT"

    def test_session_edit_route(self, client, admin_user, db):
        from app.application.academy.class_service import create_class, get_sessions
        from app.application.academy.course_service import create_course

        course = create_course(title="Route Course", num_sessions=4)
        cls = create_class(
            course_id=course.id,
            title="Route Class",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=[
                {
                    "weekday": "MONDAY",
                    "start_time": time(17, 0),
                    "end_time": time(19, 0),
                },
            ],
        )
        sessions = get_sessions(cls.id)

        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
            follow_redirects=False,
        )
        resp = client.get(f"/academy/sessions/{sessions[0].id}/edit")
        assert resp.status_code == 200
        assert b"jalali-date-input" in resp.data

    def test_session_reschedule_route(self, client, admin_user, db):
        from app.application.academy.class_service import create_class, get_sessions
        from app.application.academy.course_service import create_course

        course = create_course(title="Reschedule Course", num_sessions=4)
        cls = create_class(
            course_id=course.id,
            title="Reschedule Class",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=[
                {
                    "weekday": "MONDAY",
                    "start_time": time(17, 0),
                    "end_time": time(19, 0),
                },
            ],
        )
        sessions = get_sessions(cls.id)

        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
            follow_redirects=False,
        )
        resp = client.post(
            f"/academy/sessions/{sessions[0].id}/reschedule",
            data={
                "new_date": "1405/08/01",
                "new_start_time": "18:00",
                "new_end_time": "20:00",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302


# ---------------------------------------------------------------------------
# Part 5 — Student Profile Management
# ---------------------------------------------------------------------------


class TestStudentProfile:
    """Tests for student profile management."""

    def test_profile_page_loads(self, client, student_user):
        client.post(
            "/auth/login",
            data={"login": "student", "password": "studentpass123"},
            follow_redirects=False,
        )
        resp = client.get("/auth/profile")
        assert resp.status_code == 200
        assert b"Ali" in resp.data

    def test_profile_edit_allows_name_change(self, client, student_user):
        client.post(
            "/auth/login",
            data={"login": "student", "password": "studentpass123"},
            follow_redirects=False,
        )
        resp = client.post(
            "/auth/profile",
            data={
                "first_name": "Mohammad",
                "last_name": "Rezaei",
                "mobile_phone": "09129876543",
                "birth_date": "1385/02/25",
                "gender": "MALE",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_profile_protects_national_id(self, client, student_user):
        client.post(
            "/auth/login",
            data={"login": "student", "password": "studentpass123"},
            follow_redirects=False,
        )
        resp = client.get("/auth/profile")
        assert resp.status_code == 200
        assert b"1234567890" in resp.data

    def test_profile_requires_first_name(self, client, student_user):
        client.post(
            "/auth/login",
            data={"login": "student", "password": "studentpass123"},
            follow_redirects=False,
        )
        resp = client.post(
            "/auth/profile",
            data={
                "first_name": "",
                "last_name": "Rezaei",
                "mobile_phone": "09129876543",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_profile_shows_role_info(self, client, student_user):
        client.post(
            "/auth/login",
            data={"login": "student", "password": "studentpass123"},
            follow_redirects=False,
        )
        resp = client.get("/auth/profile")
        assert resp.status_code == 200
        assert (
            b"student" in resp.data.lower()
            or b"\xd8\xaf\xd8\xa7\xd9\x86\xd8\xb4" in resp.data
        )


# ---------------------------------------------------------------------------
# Part 8 — Persian Finance Terminology
# ---------------------------------------------------------------------------


class TestFinanceTerminology:
    """Tests for Persian finance labels in templates."""

    def test_student_finance_uses_persian_category(self, client, student_user, db):
        from app.infrastructure.database.models import FinancialTransactionModel

        tx = FinancialTransactionModel(
            student_user_id=student_user.id,
            amount=100000,
            transaction_type="CHARGE",
            category="TUITION",
            description="Test",
            status="ACTIVE",
        )
        db.session.add(tx)
        db.session.commit()

        client.post(
            "/auth/login",
            data={"login": "student", "password": "studentpass123"},
            follow_redirects=False,
        )
        resp = client.get("/finance/student/my-finance")
        assert resp.status_code == 200
        data = resp.data.decode("utf-8")
        assert "\u0634\u0647\u0631\u06cc\u0647" in data  # شهریه

    def test_persian_label_filter(self, client, admin_user):
        resp = client.get("/health")
        assert resp.status_code == 200

        from app import create_app

        app = create_app("testing")
        with app.app_context():
            from app.utils.date_utils import format_jalali

            assert format_jalali(date(2026, 9, 23)) == "1405/07/01"


# ---------------------------------------------------------------------------
# Part 9 — Home Page / Landing Page
# ---------------------------------------------------------------------------


class TestLandingPage:
    """Tests for the public landing page."""

    def test_landing_page_loads(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.data.decode("utf-8")
        assert "مدیریت" in data

    def test_landing_page_has_features(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.data.decode("utf-8")
        assert "مدیریت دوره‌ها و کلاس‌ها" in data
        assert "حضور و غیاب" in data
        assert "امور مالی" in data

    def test_landing_page_has_login_link(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"/auth/login" in resp.data

    def test_landing_page_rtl(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b'dir="rtl"' in resp.data


# ---------------------------------------------------------------------------
# Part 10 — Data Entry UX
# ---------------------------------------------------------------------------


class TestDataEntryUX:
    """Tests for improved data entry UX."""

    def test_class_form_has_required_indicators(self, client, admin_user):
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
            follow_redirects=False,
        )
        resp = client.get("/academy/classes/create")
        assert resp.status_code == 200
        assert b"required" in resp.data
        assert b"form-hint" in resp.data

    def test_session_edit_has_required_indicators(self, client, admin_user, db):
        from app.application.academy.class_service import create_class, get_sessions
        from app.application.academy.course_service import create_course

        course = create_course(title="UX Course", num_sessions=4)
        cls = create_class(
            course_id=course.id,
            title="UX Class",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=[
                {
                    "weekday": "MONDAY",
                    "start_time": time(17, 0),
                    "end_time": time(19, 0),
                },
            ],
        )
        sessions = get_sessions(cls.id)

        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
            follow_redirects=False,
        )
        resp = client.get(f"/academy/sessions/{sessions[0].id}/edit")
        assert resp.status_code == 200
        assert b"form-hint" in resp.data


# ---------------------------------------------------------------------------
# Regression Tests
# ---------------------------------------------------------------------------


class TestRegression:
    """Regression tests for existing functionality."""

    def test_auth_still_works(self, client, admin_user):
        resp = client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_class_list_still_works(self, client, admin_user):
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
            follow_redirects=False,
        )
        resp = client.get("/academy/classes")
        assert resp.status_code == 200

    def test_session_list_still_works(self, client, admin_user, db):
        from app.application.academy.class_service import create_class
        from app.application.academy.course_service import create_course

        course = create_course(title="Regression Course", num_sessions=4)
        cls = create_class(
            course_id=course.id,
            title="Regression Class",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=[
                {
                    "weekday": "MONDAY",
                    "start_time": time(17, 0),
                    "end_time": time(19, 0),
                },
            ],
        )

        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
            follow_redirects=False,
        )
        resp = client.get(f"/academy/classes/{cls.id}/sessions")
        assert resp.status_code == 200

    def test_profile_route_requires_auth(self, client):
        resp = client.get("/auth/profile", follow_redirects=False)
        assert resp.status_code == 302

    def test_student_cannot_access_admin_routes(self, client, student_user):
        client.post(
            "/auth/login",
            data={"login": "student", "password": "studentpass123"},
            follow_redirects=False,
        )
        resp = client.get("/academy/courses", follow_redirects=False)
        assert resp.status_code == 403

    def test_all_roles_still_work(
        self, client, admin_user, teacher_user, student_user, parent_user
    ):
        for login, password in [
            ("admin", "adminpass123"),
            ("teacher", "teacherpass123"),
            ("student", "studentpass123"),
            ("parent", "parentpass123"),
        ]:
            resp = client.post(
                "/auth/login",
                data={"login": login, "password": password},
                follow_redirects=False,
            )
            assert resp.status_code == 302


# ---------------------------------------------------------------------------
# P15 — Architectural Cleanup & Consistency
# ---------------------------------------------------------------------------


class TestSessionEditHistoryBugFix:
    """Tests for the fixed session edit history logic (P15 Task 1)."""

    def _create_class_with_sessions(self, db):
        from app.application.academy.class_service import create_class, get_sessions
        from app.application.academy.course_service import create_course

        course = create_course(title="Bug Course", num_sessions=4)
        cls = create_class(
            course_id=course.id,
            title="Bug Class",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=[
                {
                    "weekday": "MONDAY",
                    "start_time": time(17, 0),
                    "end_time": time(19, 0),
                },
            ],
        )
        sessions = get_sessions(cls.id)
        return cls, sessions

    def test_update_title_and_date_simultaneously(self, db, admin_user):
        from app.application.academy.class_service import update_session
        from app.infrastructure.database.models import SessionEditHistoryModel

        cls, sessions = self._create_class_with_sessions(db)
        session = sessions[0]

        original_title = session.title
        original_date = session.scheduled_date

        history = SessionEditHistoryModel.query.filter_by(session_id=session.id).count()
        assert history == 0

        result = update_session(
            session,
            title="New Title",
            scheduled_date=date(2026, 10, 15),
            edited_by=admin_user.id,
        )

        assert result.title == "New Title"
        assert result.scheduled_date == date(2026, 10, 15)
        assert result.is_rescheduled is True

        histories = SessionEditHistoryModel.query.filter_by(session_id=session.id).all()
        assert len(histories) == 1
        h = histories[0]
        assert h.previous_title == original_title
        assert h.new_title == "New Title"
        assert h.previous_date == original_date
        assert h.new_date == date(2026, 10, 15)
        assert h.change_type == "RESCHEDULE"
        assert h.edited_by == admin_user.id

    def test_update_title_and_time_simultaneously(self, db, admin_user):
        from app.application.academy.class_service import update_session
        from app.infrastructure.database.models import SessionEditHistoryModel

        cls, sessions = self._create_class_with_sessions(db)
        session = sessions[0]

        original_title = session.title
        original_start = session.start_time
        original_end = session.end_time

        result = update_session(
            session,
            title="Updated Title",
            start_time=time(14, 0),
            end_time=time(16, 0),
            edited_by=admin_user.id,
        )

        assert result.title == "Updated Title"
        assert result.start_time == time(14, 0)
        assert result.end_time == time(16, 0)

        h = SessionEditHistoryModel.query.filter_by(session_id=session.id).one()
        assert h.previous_title == original_title
        assert h.new_title == "Updated Title"
        assert h.previous_start_time == original_start
        assert h.new_start_time == time(14, 0)
        assert h.previous_end_time == original_end
        assert h.new_end_time == time(16, 0)
        assert h.change_type == "EDIT"
        assert h.previous_date is None
        assert h.new_date is None

    def test_update_all_fields_simultaneously(self, db, admin_user):
        from app.application.academy.class_service import update_session
        from app.infrastructure.database.models import SessionEditHistoryModel

        cls, sessions = self._create_class_with_sessions(db)
        session = sessions[0]

        result = update_session(
            session,
            title="All New",
            description="New desc",
            scheduled_date=date(2027, 1, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            edited_by=admin_user.id,
        )

        assert result.title == "All New"
        assert result.description == "New desc"
        assert result.scheduled_date == date(2027, 1, 1)
        assert result.start_time == time(9, 0)
        assert result.end_time == time(11, 0)

        h = SessionEditHistoryModel.query.filter_by(session_id=session.id).one()
        assert h.new_title == "All New"
        assert h.new_date == date(2027, 1, 1)
        assert h.new_start_time == time(9, 0)
        assert h.new_end_time == time(11, 0)
        assert h.change_type == "RESCHEDULE"


class TestActivityFileUploadP11:
    """Tests for P11 file management in activity submissions (P15 Task 2)."""

    def test_submit_activity_creates_stored_file(self, client, student_user, db):
        from io import BytesIO

        from app.application.academy.class_service import create_class, get_sessions
        from app.application.academy.course_service import create_course
        from app.application.activity.activity_service import create_activity
        from app.application.enrollment.enrollment_service import admin_enroll_student
        from app.infrastructure.database.models import StoredFileModel

        course = create_course(title="File Course", num_sessions=2)
        cls = create_class(
            course_id=course.id,
            title="File Class",
            start_date=date(2026, 9, 7),
            num_sessions=2,
            schedule=[
                {
                    "weekday": "MONDAY",
                    "start_time": time(17, 0),
                    "end_time": time(19, 0),
                },
            ],
        )
        sessions = get_sessions(cls.id)

        activity = create_activity(
            activity_type="HOMEWORK",
            title="File Test Activity",
            class_id=cls.id,
            session_id=sessions[0].id,
        )

        admin_enroll_student(student_user.id, cls.id)

        client.post(
            "/auth/login",
            data={"login": "student", "password": "studentpass123"},
            follow_redirects=False,
        )

        data = {
            "text_content": "Test submission",
            "files": (BytesIO(b"fake file content"), "test_file.pdf"),
        }
        resp = client.post(
            f"/activity/student/{activity.id}/submit",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200

        stored_files = StoredFileModel.query.filter_by(
            entity_type="activity_submission"
        ).all()
        assert len(stored_files) >= 1
        sf = stored_files[0]
        assert sf.original_filename == "test_file.pdf"
        assert sf.status == "ACTIVE"
        assert sf.category == "ACTIVITY_SUBMISSION"
