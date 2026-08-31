from __future__ import annotations

from datetime import date, time, timedelta

from app.extensions import db
from app.infrastructure.database.models import (
    AcademyClassModel,
    ClassScheduleModel,
    ClassSessionContentModel,
    CourseModel,
    SessionModel,
    SyllabusItemModel,
)


class ClassError(Exception):
    """Raised when a class operation fails."""


WEEKDAY_ORDER = [
    "SATURDAY",
    "SUNDAY",
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
]

WEEKDAY_TO_INDEX = {name: i for i, name in enumerate(WEEKDAY_ORDER)}

# Map our weekday names to Python's weekday() numbers (Monday=0, ..., Sunday=6)
WEEKDAY_TO_PYTHON = {
    "MONDAY": 0,
    "TUESDAY": 1,
    "WEDNESDAY": 2,
    "THURSDAY": 3,
    "FRIDAY": 4,
    "SATURDAY": 5,
    "SUNDAY": 6,
}


def _next_weekday(start: date, weekday_name: str) -> date:
    """Return the first occurrence of weekday_name on or after start."""
    target = WEEKDAY_TO_PYTHON[weekday_name]
    days_ahead = (target - start.weekday()) % 7
    return start + timedelta(days=days_ahead)


def create_class(
    course_id: int,
    title: str,
    start_date: date,
    capacity: int = 30,
    num_sessions: int | None = None,
    end_date: date | None = None,
    teacher_user_id: int | None = None,
    schedule: list[dict] | None = None,
    session_contents: list[dict] | None = None,
) -> AcademyClassModel:
    """Create a class with schedule and generate sessions.

    schedule: list of {"weekday": str, "start_time": time, "end_time": time}
    session_contents: list of {"session_number": int, "title": str, ...}
    """
    course = CourseModel.query.get(course_id)
    if course is None:
        raise ClassError("Course not found.")
    if not title or not title.strip():
        raise ClassError("Class title is required.")
    if capacity < 1:
        raise ClassError("Capacity must be at least 1.")

    effective_num_sessions = (
        num_sessions if num_sessions is not None else course.num_sessions
    )
    if effective_num_sessions < 1:
        raise ClassError("Number of sessions must be at least 1.")

    if not schedule:
        raise ClassError("At least one schedule entry is required.")

    _validate_schedule(schedule)

    academy_class = AcademyClassModel(
        course_id=course_id,
        title=title.strip(),
        start_date=start_date,
        end_date=end_date,
        capacity=capacity,
        num_sessions=effective_num_sessions,
        teacher_user_id=teacher_user_id,
    )
    db.session.add(academy_class)
    db.session.flush()

    for entry in schedule:
        sched = ClassScheduleModel(
            class_id=academy_class.id,
            weekday=entry["weekday"],
            start_time=entry["start_time"],
            end_time=entry["end_time"],
        )
        db.session.add(sched)

    if session_contents:
        for sc in session_contents:
            override = ClassSessionContentModel(
                class_id=academy_class.id,
                session_number=sc["session_number"],
                title=sc.get("title"),
                description=sc.get("description"),
                homework=sc.get("homework"),
                assessment=sc.get("assessment"),
            )
            db.session.add(override)

    db.session.flush()

    _generate_sessions(academy_class, schedule, course, session_contents)

    db.session.commit()
    return academy_class


def _validate_schedule(schedule: list[dict]) -> None:
    """Validate schedule entries."""
    valid_weekdays = set(WEEKDAY_ORDER)
    seen_weekdays: set[str] = set()

    for entry in schedule:
        weekday = entry.get("weekday")
        start_time = entry.get("start_time")
        end_time = entry.get("end_time")

        if weekday not in valid_weekdays:
            raise ClassError(f"Invalid weekday: {weekday}")
        if weekday in seen_weekdays:
            raise ClassError(f"Duplicate weekday in schedule: {weekday}")
        if not isinstance(start_time, time) or not isinstance(end_time, time):
            raise ClassError("Start and end times must be time objects.")
        if start_time >= end_time:
            raise ClassError(f"Start time must be before end time for {weekday}.")
        seen_weekdays.add(weekday)


def _generate_sessions(
    academy_class: AcademyClassModel,
    schedule: list[dict],
    course: CourseModel,
    session_contents: list[dict] | None = None,
) -> None:
    """Generate session records from the class schedule."""
    schedule_sorted = sorted(schedule, key=lambda e: WEEKDAY_TO_INDEX[e["weekday"]])

    content_map: dict[int, dict] = {}
    if session_contents:
        for sc in session_contents:
            content_map[sc["session_number"]] = sc

    syllabus_items = (
        SyllabusItemModel.query.filter_by(course_id=course.id)
        .order_by(SyllabusItemModel.order)
        .all()
    )
    syllabus_map = {item.order: item for item in syllabus_items}

    sessions: list[SessionModel] = []
    current_date = academy_class.start_date
    session_num = 1

    while session_num <= academy_class.num_sessions:
        for entry in schedule_sorted:
            if session_num > academy_class.num_sessions:
                break

            weekday = entry["weekday"]
            session_date = _next_weekday(current_date, weekday)

            if session_date < current_date:
                session_date = current_date

            override = content_map.get(session_num)
            syllabus = syllabus_map.get(session_num)

            title = None
            description = None

            if override:
                title = override.get("title") or (syllabus.title if syllabus else None)
                description = override.get("description") or (
                    syllabus.description if syllabus else None
                )
            elif syllabus:
                title = syllabus.title
                description = syllabus.description

            session = SessionModel(
                class_id=academy_class.id,
                session_number=session_num,
                scheduled_date=session_date,
                start_time=entry["start_time"],
                end_time=entry["end_time"],
                title=title,
                description=description,
            )
            db.session.add(session)
            sessions.append(session)

            session_num += 1

        current_date = current_date + timedelta(days=7)

    if sessions:
        last_date = max(s.scheduled_date for s in sessions)
        if academy_class.end_date is None:
            academy_class.end_date = last_date


def update_class(
    academy_class: AcademyClassModel,
    title: str | None = None,
    capacity: int | None = None,
    teacher_user_id: int | None = None,
    status: str | None = None,
) -> AcademyClassModel:
    """Update class metadata (not schedule or sessions)."""
    if title is not None:
        if not title.strip():
            raise ClassError("Class title cannot be empty.")
        academy_class.title = title.strip()
    if capacity is not None:
        if capacity < 1:
            raise ClassError("Capacity must be at least 1.")
        academy_class.capacity = capacity
    if teacher_user_id is not None:
        academy_class.teacher_user_id = teacher_user_id
    if status is not None:
        academy_class.status = status

    db.session.commit()
    return academy_class


def get_class(class_id: int) -> AcademyClassModel | None:
    """Get a class by ID."""
    return AcademyClassModel.query.get(class_id)


def list_classes(course_id: int | None = None) -> list[AcademyClassModel]:
    """List classes, optionally filtered by course."""
    query = AcademyClassModel.query
    if course_id is not None:
        query = query.filter_by(course_id=course_id)
    return query.order_by(AcademyClassModel.start_date.desc()).all()


def get_class_schedule(class_id: int) -> list[ClassScheduleModel]:
    """Get schedule entries for a class."""
    return (
        ClassScheduleModel.query.filter_by(class_id=class_id)
        .order_by(ClassScheduleModel.weekday)
        .all()
    )


def update_class_schedule(
    academy_class: AcademyClassModel,
    schedule: list[dict],
) -> None:
    """Replace the entire schedule for a class.

    Does NOT regenerate existing sessions — only updates the recurring pattern.
    """
    if not schedule:
        raise ClassError("At least one schedule entry is required.")
    _validate_schedule(schedule)

    ClassScheduleModel.query.filter_by(class_id=academy_class.id).delete()

    for entry in schedule:
        sched = ClassScheduleModel(
            class_id=academy_class.id,
            weekday=entry["weekday"],
            start_time=entry["start_time"],
            end_time=entry["end_time"],
        )
        db.session.add(sched)

    db.session.commit()


# ---------------------------------------------------------------------------
# Session operations
# ---------------------------------------------------------------------------


def get_sessions(class_id: int) -> list[SessionModel]:
    """Get all sessions for a class."""
    return (
        SessionModel.query.filter_by(class_id=class_id)
        .order_by(SessionModel.session_number)
        .all()
    )


def get_session(session_id: int) -> SessionModel | None:
    """Get a session by ID."""
    return SessionModel.query.get(session_id)


def reschedule_session(
    session: SessionModel,
    new_date: date,
    new_start_time: time,
    new_end_time: time,
) -> SessionModel:
    """Reschedule a single session to a new date/time.

    The recurring class schedule remains unchanged.
    """
    if new_start_time >= new_end_time:
        raise ClassError("Start time must be before end time.")

    session.scheduled_date = new_date
    session.start_time = new_start_time
    session.end_time = new_end_time
    session.is_rescheduled = True

    db.session.commit()
    return session


def update_session(
    session: SessionModel,
    title: str | None = None,
    description: str | None = None,
    scheduled_date: date | None = None,
    start_time: time | None = None,
    end_time: time | None = None,
) -> SessionModel:
    """Update session properties safely.

    Only updates provided fields. Preserves session identity and history.
    """
    if title is not None:
        session.title = title.strip() if title else None
    if description is not None:
        session.description = description.strip() if description else None
    if scheduled_date is not None:
        if scheduled_date != session.scheduled_date:
            session.is_rescheduled = True
        session.scheduled_date = scheduled_date
    if start_time is not None:
        session.start_time = start_time
    if end_time is not None:
        session.end_time = end_time

    if session.start_time >= session.end_time:
        raise ClassError("Start time must be before end time.")

    db.session.commit()
    return session


def cancel_session(session: SessionModel) -> SessionModel:
    """Cancel a session.

    The session record is preserved with CANCELLED status.
    """
    session.status = "CANCELLED"
    db.session.commit()
    return session


def complete_session(session: SessionModel) -> SessionModel:
    """Mark a session as completed."""
    session.status = "COMPLETED"
    db.session.commit()
    return session


def shift_sessions_after_cancellation(
    academy_class: AcademyClassModel,
    cancelled_session_number: int,
) -> list[SessionModel]:
    """Shift future sessions forward after a cancellation.

    The cancelled session is removed. Sessions after it are deleted and
    regenerated with sequential numbers starting from the cancelled number.
    The total number of sessions is maintained.
    """
    all_sessions = get_sessions(academy_class.id)

    cancelled = None
    for s in all_sessions:
        if s.session_number == cancelled_session_number:
            cancelled = s
            break

    if cancelled is None:
        raise ClassError(f"Session {cancelled_session_number} not found.")

    db.session.delete(cancelled)

    future_sessions = [
        s
        for s in all_sessions
        if s.session_number > cancelled_session_number and s.status != "CANCELLED"
    ]

    for s in future_sessions:
        db.session.delete(s)

    db.session.flush()

    schedule_entries = get_class_schedule(academy_class.id)
    if not schedule_entries:
        raise ClassError("Class has no schedule entries.")

    schedule_sorted = sorted(
        [
            {"weekday": s.weekday, "start_time": s.start_time, "end_time": s.end_time}
            for s in schedule_entries
        ],
        key=lambda e: WEEKDAY_TO_INDEX[e["weekday"]],
    )

    course = CourseModel.query.get(academy_class.course_id)
    syllabus_items = (
        SyllabusItemModel.query.filter_by(course_id=course.id)
        .order_by(SyllabusItemModel.order)
        .all()
    )
    syllabus_map = {item.order: item for item in syllabus_items}

    remaining = academy_class.num_sessions - cancelled_session_number + 1
    session_num = cancelled_session_number
    current_date = cancelled.scheduled_date

    while remaining > 0:
        for entry in schedule_sorted:
            if remaining <= 0:
                break

            session_date = _next_weekday(current_date, entry["weekday"])
            if session_date < current_date:
                session_date = current_date

            syllabus = syllabus_map.get(session_num)
            session = SessionModel(
                class_id=academy_class.id,
                session_number=session_num,
                scheduled_date=session_date,
                start_time=entry["start_time"],
                end_time=entry["end_time"],
                title=syllabus.title if syllabus else None,
                description=syllabus.description if syllabus else None,
                is_rescheduled=True,
            )
            db.session.add(session)
            session_num += 1
            remaining -= 1

        current_date = current_date + timedelta(days=7)

    db.session.commit()
    return get_sessions(academy_class.id)
