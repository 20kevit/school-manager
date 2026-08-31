"""Tests for Phase 23 — Academic Calendar & Semester Management."""

from datetime import date, time

import pytest

from app.application.academic_calendar.service import (
    AcademicCalendarError,
    create_academic_year,
    create_calendar_event,
    create_semester,
    delete_academic_year,
    delete_calendar_event,
    delete_semester,
    get_academic_year,
    get_active_semester,
    get_calendar_event,
    get_semester,
    is_date_holiday,
    list_academic_years,
    list_calendar_events,
    list_semesters,
    update_academic_year,
    update_calendar_event,
    update_semester,
)
from app.application.academy.class_service import (
    create_class,
    get_sessions,
    regenerate_sessions,
)
from app.application.academy.course_service import create_course
from app.infrastructure.database.models import (
    AttendanceModel,
    EnrollmentModel,
    StudentProfileModel,
    UserModel,
)

# ---------------------------------------------------------------------------
# Academic Year Tests
# ---------------------------------------------------------------------------


class TestAcademicYearCRUD:
    """Tests for Academic Year CRUD operations."""

    def test_create_academic_year(self, db):
        year = create_academic_year(
            title="1403-1404",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 6, 21),
        )
        assert year.id is not None
        assert year.title == "1403-1404"
        assert year.is_active is False

    def test_create_academic_year_active(self, db):
        year = create_academic_year(
            title="1403-1404",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 6, 21),
            is_active=True,
        )
        assert year.is_active is True

    def test_create_academic_year_deactivates_others(self, db):
        create_academic_year(
            title="1402-1403",
            start_date=date(2023, 9, 23),
            end_date=date(2024, 6, 20),
            is_active=True,
        )
        year2 = create_academic_year(
            title="1403-1404",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 6, 21),
            is_active=True,
        )
        assert year2.is_active is True
        years = list_academic_years()
        active_years = [y for y in years if y.is_active]
        assert len(active_years) == 1
        assert active_years[0].id == year2.id

    def test_create_academic_year_empty_title(self, db):
        with pytest.raises(AcademicCalendarError, match="Title is required"):
            create_academic_year(
                title="",
                start_date=date(2024, 9, 22),
                end_date=date(2025, 6, 21),
            )

    def test_create_academic_year_start_after_end(self, db):
        with pytest.raises(
            AcademicCalendarError, match="Start date must be before end date"
        ):
            create_academic_year(
                title="Bad Year",
                start_date=date(2025, 6, 21),
                end_date=date(2024, 9, 22),
            )

    def test_update_academic_year(self, db):
        year = create_academic_year(
            title="1403-1404",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 6, 21),
        )
        update_academic_year(year, title="1404-1405")
        assert year.title == "1404-1405"

    def test_get_academic_year(self, db):
        year = create_academic_year(
            title="1403-1404",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 6, 21),
        )
        fetched = get_academic_year(year.id)
        assert fetched is not None
        assert fetched.title == "1403-1404"

    def test_list_academic_years(self, db):
        create_academic_year(
            title="1402-1403",
            start_date=date(2023, 9, 23),
            end_date=date(2024, 6, 20),
        )
        create_academic_year(
            title="1403-1404",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 6, 21),
        )
        years = list_academic_years()
        assert len(years) == 2

    def test_delete_academic_year(self, db):
        year = create_academic_year(
            title="1403-1404",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 6, 21),
        )
        delete_academic_year(year)
        assert get_academic_year(year.id) is None


# ---------------------------------------------------------------------------
# Semester Tests
# ---------------------------------------------------------------------------


class TestSemesterCRUD:
    """Tests for Semester CRUD operations."""

    def _create_year(self):
        return create_academic_year(
            title="1403-1404",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 6, 21),
        )

    def test_create_semester(self, db):
        year = self._create_year()
        sem = create_semester(
            academic_year_id=year.id,
            title="نیم‌سال اول",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 1, 19),
        )
        assert sem.id is not None
        assert sem.title == "نیم‌سال اول"
        assert sem.academic_year_id == year.id

    def test_create_semester_active_deactivates_others(self, db):
        year = self._create_year()
        create_semester(
            academic_year_id=year.id,
            title="نیم‌سال اول",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 1, 19),
            is_active=True,
        )
        sem2 = create_semester(
            academic_year_id=year.id,
            title="نیم‌سال دوم",
            start_date=date(2025, 1, 20),
            end_date=date(2025, 6, 21),
            is_active=True,
        )
        assert sem2.is_active is True
        all_sems = list_semesters()
        active = [s for s in all_sems if s.is_active]
        assert len(active) == 1

    def test_create_semester_invalid_year(self, db):
        with pytest.raises(AcademicCalendarError, match="Academic year not found"):
            create_semester(
                academic_year_id=999,
                title="نیم‌سال اول",
                start_date=date(2024, 9, 22),
                end_date=date(2025, 1, 19),
            )

    def test_create_semester_start_after_end(self, db):
        year = self._create_year()
        with pytest.raises(
            AcademicCalendarError, match="Start date must be before end date"
        ):
            create_semester(
                academic_year_id=year.id,
                title="Bad Semester",
                start_date=date(2025, 1, 19),
                end_date=date(2024, 9, 22),
            )

    def test_update_semester(self, db):
        year = self._create_year()
        sem = create_semester(
            academic_year_id=year.id,
            title="نیم‌سال اول",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 1, 19),
        )
        update_semester(sem, title="نیم‌سال اول (تغییر یافته)")
        assert sem.title == "نیم‌سال اول (تغییر یافته)"

    def test_get_semester(self, db):
        year = self._create_year()
        sem = create_semester(
            academic_year_id=year.id,
            title="نیم‌سال اول",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 1, 19),
        )
        fetched = get_semester(sem.id)
        assert fetched is not None
        assert fetched.title == "نیم‌سال اول"

    def test_get_active_semester(self, db):
        year = self._create_year()
        sem = create_semester(
            academic_year_id=year.id,
            title="نیم‌سال اول",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 1, 19),
            is_active=True,
        )
        active = get_active_semester()
        assert active is not None
        assert active.id == sem.id

    def test_list_semesters_by_year(self, db):
        year = self._create_year()
        create_semester(
            academic_year_id=year.id,
            title="نیم‌سال اول",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 1, 19),
        )
        create_semester(
            academic_year_id=year.id,
            title="نیم‌سال دوم",
            start_date=date(2025, 1, 20),
            end_date=date(2025, 6, 21),
        )
        sems = list_semesters(academic_year_id=year.id)
        assert len(sems) == 2

    def test_delete_semester(self, db):
        year = self._create_year()
        sem = create_semester(
            academic_year_id=year.id,
            title="نیم‌سال اول",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 1, 19),
        )
        delete_semester(sem)
        assert get_semester(sem.id) is None


# ---------------------------------------------------------------------------
# Academic Calendar Event Tests
# ---------------------------------------------------------------------------


class TestCalendarEventCRUD:
    """Tests for Academic Calendar Event CRUD operations."""

    def test_create_calendar_event(self, db):
        event = create_calendar_event(
            title="تعطیلی نوروز",
            start_date=date(2025, 3, 21),
            end_date=date(2025, 4, 1),
            description="تعطیلات نوروزی",
        )
        assert event.id is not None
        assert event.title == "تعطیلی نوروز"
        assert event.is_recurring is False

    def test_create_single_day_event(self, db):
        event = create_calendar_event(
            title="روز معلم",
            start_date=date(2025, 5, 2),
        )
        assert event.end_date is None

    def test_create_recurring_event(self, db):
        event = create_calendar_event(
            title="۲۲ بهمن",
            start_date=date(2025, 2, 11),
            is_recurring=True,
        )
        assert event.is_recurring is True

    def test_create_event_empty_title(self, db):
        with pytest.raises(AcademicCalendarError, match="Title is required"):
            create_calendar_event(title="", start_date=date(2025, 3, 21))

    def test_create_event_start_after_end(self, db):
        with pytest.raises(
            AcademicCalendarError, match="Start date must not be after end date"
        ):
            create_calendar_event(
                title="Bad Event",
                start_date=date(2025, 4, 1),
                end_date=date(2025, 3, 21),
            )

    def test_update_calendar_event(self, db):
        event = create_calendar_event(
            title="تعطیلی نوروز",
            start_date=date(2025, 3, 21),
        )
        update_calendar_event(event, title="تعطیلات نوروزی")
        assert event.title == "تعطیلات نوروزی"

    def test_get_calendar_event(self, db):
        event = create_calendar_event(
            title="تعطیلی نوروز",
            start_date=date(2025, 3, 21),
        )
        fetched = get_calendar_event(event.id)
        assert fetched is not None

    def test_list_calendar_events(self, db):
        create_calendar_event(title="Event 1", start_date=date(2025, 3, 21))
        create_calendar_event(title="Event 2", start_date=date(2025, 4, 1))
        events = list_calendar_events()
        assert len(events) == 2

    def test_delete_calendar_event(self, db):
        event = create_calendar_event(
            title="تعطیلی نوروز",
            start_date=date(2025, 3, 21),
        )
        delete_calendar_event(event)
        assert get_calendar_event(event.id) is None


# ---------------------------------------------------------------------------
# Holiday Detection Tests
# ---------------------------------------------------------------------------


class TestHolidayDetection:
    """Tests for holiday date detection."""

    def test_single_day_holiday(self, db):
        create_calendar_event(
            title="روز معلم",
            start_date=date(2025, 5, 2),
        )
        assert is_date_holiday(date(2025, 5, 2)) is True
        assert is_date_holiday(date(2025, 5, 3)) is False

    def test_multi_day_holiday(self, db):
        create_calendar_event(
            title="تعطیلی نوروز",
            start_date=date(2025, 3, 21),
            end_date=date(2025, 3, 25),
        )
        assert is_date_holiday(date(2025, 3, 20)) is False
        assert is_date_holiday(date(2025, 3, 21)) is True
        assert is_date_holiday(date(2025, 3, 23)) is True
        assert is_date_holiday(date(2025, 3, 25)) is True
        assert is_date_holiday(date(2025, 3, 26)) is False

    def test_no_holidays(self, db):
        assert is_date_holiday(date(2025, 6, 15)) is False

    def test_overlapping_holidays(self, db):
        create_calendar_event(
            title="Holiday 1",
            start_date=date(2025, 3, 21),
            end_date=date(2025, 3, 23),
        )
        create_calendar_event(
            title="Holiday 2",
            start_date=date(2025, 3, 22),
            end_date=date(2025, 3, 25),
        )
        assert is_date_holiday(date(2025, 3, 21)) is True
        assert is_date_holiday(date(2025, 3, 22)) is True
        assert is_date_holiday(date(2025, 3, 24)) is True
        assert is_date_holiday(date(2025, 3, 26)) is False


# ---------------------------------------------------------------------------
# Session Generation with Holidays Tests
# ---------------------------------------------------------------------------


def _mon_wed_schedule():
    return [
        {"weekday": "MONDAY", "start_time": time(17, 0), "end_time": time(19, 0)},
        {"weekday": "WEDNESDAY", "start_time": time(18, 0), "end_time": time(20, 0)},
    ]


class TestSessionGenerationWithHolidays:
    """Tests for smart session generation that skips holidays."""

    def test_session_skips_single_day_holiday(self, db):
        course = create_course(title="Python", num_sessions=4)
        # 2026-09-07 is Monday, 2026-09-09 is Wednesday
        # Create a holiday on Wednesday 2026-09-09
        create_calendar_event(
            title="Holiday",
            start_date=date(2026, 9, 9),
        )
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        assert len(sessions) == 4
        # Session dates should skip Sept 9
        dates = [s.scheduled_date for s in sessions]
        assert date(2026, 9, 9) not in dates
        assert date(2026, 9, 7) in dates  # Monday
        assert date(2026, 9, 14) in dates  # Next Monday
        assert date(2026, 9, 16) in dates  # Next Wednesday (after 9th skipped)

    def test_session_skips_multi_day_holiday(self, db):
        course = create_course(title="Python", num_sessions=6)
        # Start on Monday 2026-09-07
        # Holiday from Tuesday 2026-09-08 to Thursday 2026-09-10
        create_calendar_event(
            title="5-day Holiday",
            start_date=date(2026, 9, 8),
            end_date=date(2026, 9, 10),
        )
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            num_sessions=6,
            schedule=[
                {
                    "weekday": "MONDAY",
                    "start_time": time(17, 0),
                    "end_time": time(19, 0),
                },
                {
                    "weekday": "TUESDAY",
                    "start_time": time(17, 0),
                    "end_time": time(19, 0),
                },
                {
                    "weekday": "WEDNESDAY",
                    "start_time": time(17, 0),
                    "end_time": time(19, 0),
                },
            ],
        )
        sessions = get_sessions(cls.id)
        assert len(sessions) == 6
        dates = [s.scheduled_date for s in sessions]
        # Sept 8, 9, 10 should all be skipped
        for d in [date(2026, 9, 8), date(2026, 9, 9), date(2026, 9, 10)]:
            assert d not in dates

    def test_no_holidays_generates_normally(self, db):
        course = create_course(title="Python", num_sessions=4)
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        assert len(sessions) == 4
        # Should have Sept 7 (Mon), Sept 9 (Wed), Sept 14 (Mon), Sept 16 (Wed)
        dates = [s.scheduled_date for s in sessions]
        assert dates == [
            date(2026, 9, 7),
            date(2026, 9, 9),
            date(2026, 9, 14),
            date(2026, 9, 16),
        ]


# ---------------------------------------------------------------------------
# Regenerate Sessions Tests
# ---------------------------------------------------------------------------


class TestRegenerateSessions:
    """Tests for session regeneration with attendance preservation."""

    def test_regenerate_preserves_past_sessions(self, db):
        course = create_course(title="Python", num_sessions=4)
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 1, 5),  # Monday in the past
            num_sessions=4,
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        assert len(sessions) == 4

        # Simulate past sessions by not modifying dates (they're already in the past)
        # Regenerate should not delete past sessions
        regenerated = regenerate_sessions(cls)
        # All sessions should be preserved since they are in the past
        assert len(regenerated) == 4

    def test_regenerate_with_attendance_preserved(self, db):
        course = create_course(title="Python", num_sessions=4)
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        assert len(sessions) == 4

        # Create a student and enrollment for attendance
        user = UserModel(login="student1")
        user.set_password("pass123")
        role = __import__(
            "app.infrastructure.database.models", fromlist=["RoleModel"]
        ).RoleModel(name="STUDENT")
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
        db.session.flush()

        enrollment = EnrollmentModel(
            student_user_id=user.id,
            class_id=cls.id,
            status="APPROVED",
        )
        db.session.add(enrollment)
        db.session.flush()

        # Add attendance for session 1
        attendance = AttendanceModel(
            enrollment_id=enrollment.id,
            session_id=sessions[0].id,
            status="PRESENT",
        )
        db.session.add(attendance)
        db.session.flush()

        # Add holiday on session 3's date (Wednesday 2026-09-09)
        create_calendar_event(
            title="Holiday",
            start_date=date(2026, 9, 9),
        )

        regenerated = regenerate_sessions(cls)

        # Session 1 with attendance should be preserved
        preserved_dates = [s.scheduled_date for s in regenerated]
        assert date(2026, 9, 7) in preserved_dates  # Session 1 preserved

        # All 4 sessions should exist
        assert len(regenerated) == 4

    def test_regenerate_no_schedule(self, db):
        course = create_course(title="Python", num_sessions=4)
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=_mon_wed_schedule(),
        )
        # Delete all schedule entries
        from app.infrastructure.database.models import ClassScheduleModel

        ClassScheduleModel.query.filter_by(class_id=cls.id).delete()
        db.session.flush()

        regenerated = regenerate_sessions(cls)
        # All sessions are future with no attendance, so they get deleted
        # No schedule means nothing new is created
        assert len(regenerated) == 0


# ---------------------------------------------------------------------------
# Admin Route Tests
# ---------------------------------------------------------------------------


class TestAdminCalendarRoutes:
    """Tests for admin academic calendar routes."""

    def _login(self, client, admin_user):
        with client.session_transaction():
            # Simulate login
            pass
        client.post(
            "/auth/login",
            data={"login": admin_user.login, "password": "adminpass123"},
            follow_redirects=True,
        )

    def test_year_list_requires_admin(self, client, db):
        resp = client.get("/admin/years")
        assert resp.status_code in (302, 403)

    def test_calendar_list_requires_admin(self, client, db):
        resp = client.get("/admin/calendar")
        assert resp.status_code in (302, 403)

    def test_semester_list_requires_admin(self, client, db):
        resp = client.get("/admin/semesters")
        assert resp.status_code in (302, 403)

    def test_year_list_as_admin(self, client, admin_user, db):
        self._login(client, admin_user)
        resp = client.get("/admin/years")
        assert resp.status_code == 200

    def test_calendar_list_as_admin(self, client, admin_user, db):
        self._login(client, admin_user)
        resp = client.get("/admin/calendar")
        assert resp.status_code == 200

    def test_semester_list_as_admin(self, client, admin_user, db):
        self._login(client, admin_user)
        resp = client.get("/admin/semesters")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Semester on AcademyClass Tests
# ---------------------------------------------------------------------------


class TestClassSemesterAssociation:
    """Tests for associating classes with semesters."""

    def test_class_with_semester(self, db):
        year = create_academic_year(
            title="1403-1404",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 6, 21),
        )
        sem = create_semester(
            academic_year_id=year.id,
            title="نیم‌سال اول",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 1, 19),
        )
        course = create_course(title="Python", num_sessions=4)
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            semester_id=sem.id,
            schedule=_mon_wed_schedule(),
        )
        assert cls.semester_id == sem.id

    def test_class_without_semester(self, db):
        course = create_course(title="Python", num_sessions=4)
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=_mon_wed_schedule(),
        )
        assert cls.semester_id is None

    def test_list_classes_by_semester(self, db):
        year = create_academic_year(
            title="1403-1404",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 6, 21),
        )
        sem = create_semester(
            academic_year_id=year.id,
            title="نیم‌سال اول",
            start_date=date(2024, 9, 22),
            end_date=date(2025, 1, 19),
        )
        course = create_course(title="Python", num_sessions=4)

        create_class(
            course_id=course.id,
            title="Class A",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            semester_id=sem.id,
            schedule=_mon_wed_schedule(),
        )
        create_class(
            course_id=course.id,
            title="Class B",
            start_date=date(2026, 9, 14),
            num_sessions=4,
            schedule=_mon_wed_schedule(),
        )

        from app.application.academy.class_service import list_classes

        all_classes = list_classes()
        assert len(all_classes) == 2

        sem_classes = list_classes(semester_id=sem.id)
        assert len(sem_classes) == 1
        assert sem_classes[0].title == "Class A"
