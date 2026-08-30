from __future__ import annotations

from datetime import date, time
from enum import StrEnum


class ClassStatus(StrEnum):
    """Status of an academy class."""

    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Weekday(StrEnum):
    """Days of the week for scheduling."""

    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"


class AcademyClass:
    """Class domain entity.

    Represents an actual running class created from a Course template.
    """

    def __init__(
        self,
        id: int | None,
        course_id: int,
        title: str,
        start_date: date,
        end_date: date | None = None,
        capacity: int = 30,
        num_sessions: int = 1,
        status: ClassStatus = ClassStatus.PLANNED,
        teacher_user_id: int | None = None,
    ):
        self.id = id
        self.course_id = course_id
        self.title = title
        self.start_date = start_date
        self.end_date = end_date
        self.capacity = capacity
        self.num_sessions = num_sessions
        self.status = status
        self.teacher_user_id = teacher_user_id

    def __repr__(self) -> str:
        return f"<AcademyClass id={self.id} title={self.title!r}>"


class ClassSchedule:
    """Weekly schedule entry for a class.

    Represents one recurring weekly time slot (e.g., Monday 17:00-19:00).
    """

    def __init__(
        self,
        id: int | None,
        class_id: int,
        weekday: Weekday,
        start_time: time,
        end_time: time,
    ):
        self.id = id
        self.class_id = class_id
        self.weekday = weekday
        self.start_time = start_time
        self.end_time = end_time

    def __repr__(self) -> str:
        return (
            f"<ClassSchedule id={self.id} {self.weekday} "
            f"{self.start_time}-{self.end_time}>"
        )


class ClassSessionContent:
    """Class-specific session content override.

    Allows customizing syllabus content at the class level.
    """

    def __init__(
        self,
        id: int | None,
        class_id: int,
        session_number: int,
        title: str | None = None,
        description: str | None = None,
        homework: str | None = None,
        assessment: str | None = None,
    ):
        self.id = id
        self.class_id = class_id
        self.session_number = session_number
        self.title = title
        self.description = description
        self.homework = homework
        self.assessment = assessment

    def __repr__(self) -> str:
        return f"<ClassSessionContent id={self.id} session={self.session_number}>"
