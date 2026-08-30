from __future__ import annotations

from datetime import datetime
from enum import StrEnum


class ActivityType(StrEnum):
    """Type of learning activity."""

    HOMEWORK = "HOMEWORK"
    PROJECT = "PROJECT"
    PRACTICE = "PRACTICE"
    QUIZ = "QUIZ"
    EXAM = "EXAM"


class ActivityRequirement(StrEnum):
    """Whether an activity is required or optional."""

    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"


class SubmissionStatus(StrEnum):
    """Status of a student submission."""

    NOT_SUBMITTED = "NOT_SUBMITTED"
    SUBMITTED = "SUBMITTED"
    LATE = "LATE"
    GRADED = "GRADED"
    RETURNED = "RETURNED"


class Activity:
    """Activity domain entity.

    Represents a learning activity (homework, project, quiz, etc.)
    that can be associated with a Course, Class, or Session.
    """

    def __init__(
        self,
        id: int | None,
        activity_type: ActivityType,
        title: str,
        description: str = "",
        requirement: ActivityRequirement = ActivityRequirement.REQUIRED,
        deadline: datetime | None = None,
        max_score: float = 100.0,
        is_active: bool = True,
        sort_order: int = 0,
        course_id: int | None = None,
        class_id: int | None = None,
        session_id: int | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.activity_type = activity_type
        self.title = title
        self.description = description
        self.requirement = requirement
        self.deadline = deadline
        self.max_score = max_score
        self.is_active = is_active
        self.sort_order = sort_order
        self.course_id = course_id
        self.class_id = class_id
        self.session_id = session_id
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def deactivate(self) -> None:
        """Soft-disable the activity without deleting it."""
        self.is_active = False

    def __repr__(self) -> str:
        return f"<Activity id={self.id} type={self.activity_type} title={self.title!r}>"
