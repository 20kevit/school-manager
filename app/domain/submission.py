from __future__ import annotations

from datetime import datetime

from app.domain.activity import SubmissionStatus


class ActivitySubmission:
    """ActivitySubmission domain entity.

    Represents a student's submission attempt for an activity.
    Each new submission creates a new version; previous versions are preserved.
    """

    def __init__(
        self,
        id: int | None,
        activity_id: int,
        student_user_id: int,
        enrollment_id: int,
        text_content: str = "",
        submitted_at: datetime | None = None,
        status: SubmissionStatus = SubmissionStatus.NOT_SUBMITTED,
        score: float | None = None,
        feedback: str = "",
        graded_at: datetime | None = None,
        graded_by: int | None = None,
        version: int = 1,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.activity_id = activity_id
        self.student_user_id = student_user_id
        self.enrollment_id = enrollment_id
        self.text_content = text_content
        self.submitted_at = submitted_at
        self.status = status
        self.score = score
        self.feedback = feedback
        self.graded_at = graded_at
        self.graded_by = graded_by
        self.version = version
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def __repr__(self) -> str:
        return (
            f"<ActivitySubmission id={self.id} activity={self.activity_id} "
            f"student={self.student_user_id} version={self.version}>"
        )
