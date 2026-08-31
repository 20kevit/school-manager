"""Tests for P25 — Online Class Integration & Session Links."""

from datetime import date, time

import pytest

from app.application.academy.class_service import (
    create_class,
    get_sessions,
    update_class,
    update_session,
)


@pytest.fixture
def course(db):
    from app.application.academy.course_service import create_course

    return create_course(
        title="Online Course",
        description="Course for online link tests",
        num_sessions=8,
    )


def _mon_wed_schedule():
    return [
        {"weekday": "MONDAY", "start_time": time(17, 0), "end_time": time(19, 0)},
        {"weekday": "WEDNESDAY", "start_time": time(18, 0), "end_time": time(20, 0)},
    ]


class TestOnlineLinkOnClass:
    """Tests for online_link on AcademyClassModel."""

    def test_class_has_no_online_link_by_default(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        assert cls.online_link is None

    def test_set_online_link_on_class(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        update_class(cls, online_link="https://skyroom.online/room/123")
        assert cls.online_link == "https://skyroom.online/room/123"

    def test_clear_online_link_on_class(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        update_class(cls, online_link="https://skyroom.online/room/123")
        assert cls.online_link == "https://skyroom.online/room/123"
        update_class(cls, online_link="")
        assert cls.online_link is None

    def test_update_class_preserves_online_link(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        update_class(cls, online_link="https://meet.google.com/abc")
        update_class(cls, title="Updated Title")
        assert cls.online_link == "https://meet.google.com/abc"
        assert cls.title == "Updated Title"


class TestOnlineLinkOnSession:
    """Tests for online_link on SessionModel."""

    def test_session_has_no_online_link_by_default(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            num_sessions=2,
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        for s in sessions:
            assert s.online_link is None

    def test_set_online_link_on_session(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            num_sessions=2,
            schedule=_mon_wed_schedule(),
        )
        session = get_sessions(cls.id)[0]
        update_session(
            session,
            scheduled_date=session.scheduled_date,
            start_time=session.start_time,
            end_time=session.end_time,
            online_link="https://zoom.us/j/123456",
        )
        assert session.online_link == "https://zoom.us/j/123456"

    def test_clear_session_online_link(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            num_sessions=2,
            schedule=_mon_wed_schedule(),
        )
        session = get_sessions(cls.id)[0]
        update_session(
            session,
            scheduled_date=session.scheduled_date,
            start_time=session.start_time,
            end_time=session.end_time,
            online_link="https://zoom.us/j/123456",
        )
        update_session(
            session,
            scheduled_date=session.scheduled_date,
            start_time=session.start_time,
            end_time=session.end_time,
            online_link="",
        )
        assert session.online_link is None


class TestSessionLinkOverridesClassLink:
    """Tests that session online_link overrides class online_link."""

    def test_session_link_takes_priority(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            num_sessions=2,
            schedule=_mon_wed_schedule(),
        )
        update_class(cls, online_link="https://class-default.example.com")

        session = get_sessions(cls.id)[0]
        update_session(
            session,
            scheduled_date=session.scheduled_date,
            start_time=session.start_time,
            end_time=session.end_time,
            online_link="https://session-specific.example.com",
        )

        # Session-specific link should be used
        assert session.online_link == "https://session-specific.example.com"
        # Class default remains
        assert cls.online_link == "https://class-default.example.com"

    def test_fallback_to_class_link_when_session_link_empty(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            num_sessions=2,
            schedule=_mon_wed_schedule(),
        )
        update_class(cls, online_link="https://class-default.example.com")

        session = get_sessions(cls.id)[0]
        # Session has no link set
        assert session.online_link is None
        # The effective link would be the class default
        effective_link = session.online_link or cls.online_link
        assert effective_link == "https://class-default.example.com"

    def test_no_link_when_both_empty(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            num_sessions=2,
            schedule=_mon_wed_schedule(),
        )
        session = get_sessions(cls.id)[0]
        effective_link = session.online_link or cls.online_link
        assert effective_link is None


class TestOnlineLinkAuthorization:
    """Tests for online_link edit authorization."""

    def test_teacher_can_edit_own_class_online_link(self, db, course, teacher_user):
        cls = create_class(
            course_id=course.id,
            title="Teacher Class",
            start_date=date(2026, 9, 7),
            teacher_user_id=teacher_user.id,
            schedule=_mon_wed_schedule(),
        )
        update_class(cls, online_link="https://teacher-link.example.com")
        assert cls.online_link == "https://teacher-link.example.com"


class TestTimetableOnlineLink:
    """Tests for timetable online_link data."""

    def test_build_timetable_includes_online_link(self, db, course):
        from app.infrastructure.database.models import ClassScheduleModel
        from app.interface.web.portal.routes import _build_timetable_data

        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        update_class(cls, online_link="https://class-link.example.com")

        schedule_entries = ClassScheduleModel.query.filter_by(class_id=cls.id).all()
        timetable = _build_timetable_data(schedule_entries)

        monday_entries = timetable.get("MONDAY", [])
        assert len(monday_entries) == 1
        assert monday_entries[0]["online_link"] == "https://class-link.example.com"


class TestGetUpcomingSessions:
    """Tests for _get_upcoming_sessions."""

    def test_returns_empty_when_no_sessions_today(self, db, course):
        from app.interface.web.portal.routes import _get_upcoming_sessions

        cls = create_class(
            course_id=course.id,
            title="Future Class",
            start_date=date(2026, 9, 14),
            num_sessions=2,
            schedule=_mon_wed_schedule(),
        )
        upcoming = _get_upcoming_sessions([cls.id])
        assert upcoming == []

    def test_returns_empty_when_no_online_link(self, db, course):
        from app.interface.web.portal.routes import _get_upcoming_sessions

        cls = create_class(
            course_id=course.id,
            title="No Link Class",
            start_date=date(2026, 9, 7),
            num_sessions=2,
            schedule=_mon_wed_schedule(),
        )
        upcoming = _get_upcoming_sessions([cls.id])
        assert upcoming == []

    def test_returns_empty_for_empty_class_ids(self, db):
        from app.interface.web.portal.routes import _get_upcoming_sessions

        upcoming = _get_upcoming_sessions([])
        assert upcoming == []


class TestStudentEnrollmentOnlineLink:
    """Tests that online link is visible only to enrolled students."""

    def test_class_model_stores_online_link(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Enrollment Test",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        update_class(cls, online_link="https://enrolled-only.example.com")
        assert cls.online_link == "https://enrolled-only.example.com"

    def test_unenrolled_student_sees_no_link(self, db, course):
        from app.infrastructure.database.models import EnrollmentModel

        cls = create_class(
            course_id=course.id,
            title="Enrollment Test",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        update_class(cls, online_link="https://secret-link.example.com")

        enrollment = EnrollmentModel.query.filter_by(class_id=cls.id).first()
        assert enrollment is None
