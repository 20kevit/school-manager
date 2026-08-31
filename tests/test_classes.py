"""Tests for Class, Schedule, and Session services."""

from datetime import date, time

import pytest

from app.application.academy.class_service import (
    ClassError,
    cancel_session,
    complete_session,
    create_class,
    get_class,
    get_session,
    get_sessions,
    list_classes,
    reschedule_session,
    shift_sessions_after_cancellation,
    update_class,
    update_class_schedule,
)
from app.application.academy.course_service import create_course


@pytest.fixture
def course(db):
    return create_course(
        title="Python Beginner",
        description="Intro to Python",
        num_sessions=8,
    )


@pytest.fixture
def course_with_syllabus(db):
    from app.application.academy.course_service import add_syllabus_item

    course = create_course(title="Python Course", num_sessions=4)
    add_syllabus_item(course, order=1, title="Introduction to Python")
    add_syllabus_item(course, order=2, title="Variables and Types")
    add_syllabus_item(course, order=3, title="Control Flow")
    add_syllabus_item(course, order=4, title="Functions")
    return course


def _mon_wed_schedule():
    return [
        {"weekday": "MONDAY", "start_time": time(17, 0), "end_time": time(19, 0)},
        {"weekday": "WEDNESDAY", "start_time": time(18, 0), "end_time": time(20, 0)},
    ]


class TestClassCreation:
    """Tests for class creation."""

    def test_create_class_basic(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Python Group A",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        assert cls.id is not None
        assert cls.title == "Python Group A"
        assert cls.course_id == course.id
        assert cls.capacity == 30
        assert cls.status == "PLANNED"

    def test_create_class_with_custom_sessions(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Short Course",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=_mon_wed_schedule(),
        )
        assert cls.num_sessions == 4
        sessions = get_sessions(cls.id)
        assert len(sessions) == 4

    def test_create_class_generates_sessions(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        assert len(sessions) == 4
        assert sessions[0].session_number == 1
        assert sessions[3].session_number == 4

    def test_create_class_session_dates(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),  # Monday
            num_sessions=4,
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        assert sessions[0].scheduled_date == date(2026, 9, 7)  # Monday
        assert sessions[1].scheduled_date == date(2026, 9, 9)  # Wednesday
        assert sessions[2].scheduled_date == date(2026, 9, 14)  # Monday
        assert sessions[3].scheduled_date == date(2026, 9, 16)  # Wednesday

    def test_create_class_session_times(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        assert sessions[0].start_time == time(17, 0)
        assert sessions[0].end_time == time(19, 0)
        assert sessions[1].start_time == time(18, 0)
        assert sessions[1].end_time == time(20, 0)

    def test_create_class_sets_end_date(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test Class",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=_mon_wed_schedule(),
        )
        assert cls.end_date is not None
        assert cls.end_date == date(2026, 9, 16)

    def test_create_class_invalid_course_fails(self, db):
        with pytest.raises(ClassError, match="Course not found"):
            create_class(
                course_id=9999,
                title="Test",
                start_date=date(2026, 9, 7),
                schedule=_mon_wed_schedule(),
            )

    def test_create_class_empty_title_fails(self, db, course):
        with pytest.raises(ClassError, match="title is required"):
            create_class(
                course_id=course.id,
                title="",
                start_date=date(2026, 9, 7),
                schedule=_mon_wed_schedule(),
            )

    def test_create_class_zero_capacity_fails(self, db, course):
        with pytest.raises(ClassError, match="Capacity must be at least 1"):
            create_class(
                course_id=course.id,
                title="Test",
                start_date=date(2026, 9, 7),
                capacity=0,
                schedule=_mon_wed_schedule(),
            )

    def test_create_class_no_schedule_fails(self, db, course):
        with pytest.raises(ClassError, match="At least one schedule"):
            create_class(
                course_id=course.id,
                title="Test",
                start_date=date(2026, 9, 7),
                schedule=[],
            )

    def test_create_class_duplicate_weekday_fails(self, db, course):
        schedule = [
            {"weekday": "MONDAY", "start_time": time(17, 0), "end_time": time(19, 0)},
            {"weekday": "MONDAY", "start_time": time(18, 0), "end_time": time(20, 0)},
        ]
        with pytest.raises(ClassError, match="Duplicate weekday"):
            create_class(
                course_id=course.id,
                title="Test",
                start_date=date(2026, 9, 7),
                schedule=schedule,
            )

    def test_create_class_invalid_weekday_fails(self, db, course):
        schedule = [
            {"weekday": "INVALID", "start_time": time(17, 0), "end_time": time(19, 0)},
        ]
        with pytest.raises(ClassError, match="Invalid weekday"):
            create_class(
                course_id=course.id,
                title="Test",
                start_date=date(2026, 9, 7),
                schedule=schedule,
            )

    def test_create_class_start_after_end_fails(self, db, course):
        schedule = [
            {"weekday": "MONDAY", "start_time": time(19, 0), "end_time": time(17, 0)},
        ]
        with pytest.raises(ClassError, match="Start time must be before"):
            create_class(
                course_id=course.id,
                title="Test",
                start_date=date(2026, 9, 7),
                schedule=schedule,
            )

    def test_create_class_with_teacher(self, db, course, teacher_user):
        cls = create_class(
            course_id=course.id,
            title="With Teacher",
            start_date=date(2026, 9, 7),
            teacher_user_id=teacher_user.id,
            schedule=_mon_wed_schedule(),
        )
        assert cls.teacher_user_id == teacher_user.id


class TestClassUpdate:
    """Tests for class updates."""

    def test_update_class_title(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Old Title",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        update_class(cls, title="New Title")
        assert cls.title == "New Title"

    def test_update_class_capacity(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            capacity=20,
            schedule=_mon_wed_schedule(),
        )
        update_class(cls, capacity=40)
        assert cls.capacity == 40

    def test_update_class_status(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        update_class(cls, status="ACTIVE")
        assert cls.status == "ACTIVE"

    def test_update_class_empty_title_fails(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        with pytest.raises(ClassError, match="cannot be empty"):
            update_class(cls, title="")


class TestScheduleUpdate:
    """Tests for schedule updates."""

    def test_update_schedule(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        new_schedule = [
            {"weekday": "TUESDAY", "start_time": time(16, 0), "end_time": time(18, 0)},
        ]
        update_class_schedule(cls, new_schedule)
        from app.application.academy.class_service import get_class_schedule

        schedule = get_class_schedule(cls.id)
        assert len(schedule) == 1
        assert schedule[0].weekday == "TUESDAY"

    def test_update_schedule_empty_fails(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        with pytest.raises(ClassError, match="At least one schedule"):
            update_class_schedule(cls, [])


class TestSessionOperations:
    """Tests for session operations."""

    def test_get_sessions(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        assert len(sessions) == 4

    def test_get_session(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            num_sessions=2,
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        session = get_session(sessions[0].id)
        assert session is not None
        assert session.session_number == 1

    def test_reschedule_session(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            num_sessions=2,
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        session = sessions[0]
        reschedule_session(session, date(2026, 9, 10), time(20, 0), time(22, 0))
        assert session.scheduled_date == date(2026, 9, 10)
        assert session.start_time == time(20, 0)
        assert session.end_time == time(22, 0)
        assert session.is_rescheduled is True

    def test_reschedule_session_invalid_time_fails(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            num_sessions=2,
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        with pytest.raises(ClassError, match="Start time must be before"):
            reschedule_session(sessions[0], date(2026, 9, 10), time(22, 0), time(20, 0))

    def test_cancel_session(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            num_sessions=2,
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        cancel_session(sessions[0])
        assert sessions[0].status == "CANCELLED"

    def test_complete_session(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            num_sessions=2,
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        complete_session(sessions[0])
        assert sessions[0].status == "COMPLETED"

    def test_cancelled_session_preserved(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        cancel_session(sessions[1])
        all_sessions = get_sessions(cls.id)
        assert len(all_sessions) == 4
        cancelled = [s for s in all_sessions if s.status == "CANCELLED"]
        assert len(cancelled) == 1


class TestSessionShifting:
    """Tests for session shifting after cancellation."""

    def test_shift_after_cancellation(self, db, course_with_syllabus):
        cls = create_class(
            course_id=course_with_syllabus.id,
            title="Shift Test",
            start_date=date(2026, 9, 7),  # Monday
            num_sessions=4,
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        assert len(sessions) == 4
        assert sessions[0].session_number == 1
        assert sessions[1].session_number == 2
        assert sessions[2].session_number == 3
        assert sessions[3].session_number == 4

        shift_sessions_after_cancellation(cls, 2)

        remaining = get_sessions(cls.id)
        assert len(remaining) == 4
        assert remaining[0].session_number == 1
        assert remaining[1].session_number == 2
        assert remaining[2].session_number == 3
        assert remaining[3].session_number == 4

    def test_shift_preserves_schedule(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Schedule Test",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=_mon_wed_schedule(),
        )
        shift_sessions_after_cancellation(cls, 1)
        from app.application.academy.class_service import get_class_schedule

        schedule = get_class_schedule(cls.id)
        assert len(schedule) == 2
        weekdays = {s.weekday for s in schedule}
        assert weekdays == {"MONDAY", "WEDNESDAY"}

    def test_shift_nonexistent_session_fails(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            num_sessions=2,
            schedule=_mon_wed_schedule(),
        )
        with pytest.raises(ClassError, match="not found"):
            shift_sessions_after_cancellation(cls, 99)


class TestSessionContentOverrides:
    """Tests for session content overrides."""

    def test_create_class_with_content_overrides(self, db, course):
        contents = [
            {
                "session_number": 1,
                "title": "Custom Intro",
                "description": "Custom desc",
            },
            {"session_number": 2, "title": "Custom Variables"},
        ]
        cls = create_class(
            course_id=course.id,
            title="With Content",
            start_date=date(2026, 9, 7),
            num_sessions=4,
            schedule=_mon_wed_schedule(),
            session_contents=contents,
        )
        sessions = get_sessions(cls.id)
        assert sessions[0].title == "Custom Intro"
        assert sessions[0].description == "Custom desc"
        assert sessions[1].title == "Custom Variables"


class TestClassQuery:
    """Tests for class queries."""

    def test_list_classes(self, db, course):
        create_class(
            course_id=course.id,
            title="Class 1",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        create_class(
            course_id=course.id,
            title="Class 2",
            start_date=date(2026, 10, 7),
            schedule=_mon_wed_schedule(),
        )
        classes = list_classes()
        assert len(classes) == 2

    def test_list_classes_by_course(self, db):
        course1 = create_course(title="Course 1")
        course2 = create_course(title="Course 2")
        create_class(
            course_id=course1.id,
            title="Class 1",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        create_class(
            course_id=course2.id,
            title="Class 2",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        classes = list_classes(course_id=course1.id)
        assert len(classes) == 1
        assert classes[0].title == "Class 1"

    def test_get_class(self, db, course):
        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        fetched = get_class(cls.id)
        assert fetched is not None
        assert fetched.title == "Test"

    def test_get_nonexistent_class(self, db):
        assert get_class(9999) is None


class TestSessionEditing:
    """Tests for session editing functionality."""

    def test_update_session_title_and_description(self, db, course):
        from app.application.academy.class_service import update_session

        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        session = sessions[0]

        updated = update_session(session, title="New Title", description="New Desc")
        assert updated.title == "New Title"
        assert updated.description == "New Desc"

    def test_update_session_date(self, db, course):
        from app.application.academy.class_service import update_session

        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        session = sessions[0]

        new_date = date(2026, 10, 1)
        updated = update_session(session, scheduled_date=new_date)
        assert updated.scheduled_date == new_date
        assert updated.is_rescheduled is True

    def test_update_session_time_validation(self, db, course):
        from app.application.academy.class_service import update_session

        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        session = sessions[0]

        with pytest.raises(ClassError):
            update_session(
                session,
                start_time=time(14, 0),
                end_time=time(12, 0),
            )

    def test_clear_session_title(self, db, course):
        from app.application.academy.class_service import update_session

        cls = create_class(
            course_id=course.id,
            title="Test",
            start_date=date(2026, 9, 7),
            schedule=_mon_wed_schedule(),
        )
        sessions = get_sessions(cls.id)
        session = sessions[0]

        updated = update_session(session, title="Has Title")
        assert updated.title == "Has Title"
        updated2 = update_session(updated, title="")
        assert updated2.title is None
