from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum


class AssessmentType(StrEnum):
    """Type of academic assessment."""

    FINAL_EXAM = "FINAL_EXAM"
    MIDTERM = "MIDTERM"
    QUIZ = "QUIZ"
    PROJECT = "PROJECT"
    PRACTICAL = "PRACTICAL"
    ORAL = "ORAL"
    OTHER = "OTHER"


class AssessmentStatus(StrEnum):
    """Lifecycle status of an assessment."""

    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    GRADED = "GRADED"
    CANCELLED = "CANCELLED"


class Assessment:
    """Assessment domain entity.

    Represents an academic evaluation (final exam, midterm, quiz, etc.)
    that belongs to a specific Class.
    """

    def __init__(
        self,
        id: int | None,
        class_id: int,
        assessment_type: AssessmentType,
        title: str,
        description: str = "",
        scheduled_date: date | None = None,
        scheduled_time: datetime | None = None,
        duration_minutes: int | None = None,
        max_score: float = 100.0,
        passing_score: float = 60.0,
        status: AssessmentStatus = AssessmentStatus.DRAFT,
        created_by: int | None = None,
        notes: str = "",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.class_id = class_id
        self.assessment_type = assessment_type
        self.title = title
        self.description = description
        self.scheduled_date = scheduled_date
        self.scheduled_time = scheduled_time
        self.duration_minutes = duration_minutes
        self.max_score = max_score
        self.passing_score = passing_score
        self.status = status
        self.created_by = created_by
        self.notes = notes
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def can_transition_to(self, new_status: AssessmentStatus) -> bool:
        """Check if a status transition is valid."""
        valid_transitions = {
            AssessmentStatus.DRAFT: {
                AssessmentStatus.SCHEDULED,
                AssessmentStatus.CANCELLED,
            },
            AssessmentStatus.SCHEDULED: {
                AssessmentStatus.OPEN,
                AssessmentStatus.CANCELLED,
            },
            AssessmentStatus.OPEN: {
                AssessmentStatus.CLOSED,
                AssessmentStatus.CANCELLED,
            },
            AssessmentStatus.CLOSED: {
                AssessmentStatus.GRADED,
            },
        }
        return new_status in valid_transitions.get(self.status, set())

    def __repr__(self) -> str:
        return (
            f"<Assessment id={self.id} type={self.assessment_type} "
            f"title={self.title!r} class={self.class_id}>"
        )
