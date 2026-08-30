from __future__ import annotations

from datetime import datetime
from enum import StrEnum


class ResultStatus(StrEnum):
    """Status of an assessment result."""

    NOT_GRADED = "NOT_GRADED"
    GRADED = "GRADED"
    CORRECTED = "CORRECTED"


class PresenceStatus(StrEnum):
    """Student presence status for an assessment."""

    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    EXCUSED = "EXCUSED"


class PassFailStatus(StrEnum):
    """Pass/fail determination for a result."""

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_DETERMINED = "NOT_DETERMINED"


class AssessmentResult:
    """AssessmentResult domain entity.

    Represents a student's result in a specific assessment.
    Linked via an Enrollment (student must be enrolled in the assessment's class).
    """

    def __init__(
        self,
        id: int | None,
        assessment_id: int,
        enrollment_id: int,
        student_user_id: int,
        score: float | None = None,
        max_score: float = 100.0,
        percentage: float | None = None,
        result_status: ResultStatus = ResultStatus.NOT_GRADED,
        presence_status: PresenceStatus = PresenceStatus.PRESENT,
        pass_fail: PassFailStatus = PassFailStatus.NOT_DETERMINED,
        comments: str = "",
        graded_by: int | None = None,
        graded_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.assessment_id = assessment_id
        self.enrollment_id = enrollment_id
        self.student_user_id = student_user_id
        self.score = score
        self.max_score = max_score
        self.percentage = percentage
        self.result_status = result_status
        self.presence_status = presence_status
        self.pass_fail = pass_fail
        self.comments = comments
        self.graded_by = graded_by
        self.graded_at = graded_at
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def __repr__(self) -> str:
        return (
            f"<AssessmentResult id={self.id} assessment={self.assessment_id} "
            f"student={self.student_user_id} score={self.score}>"
        )


class GradeHistory:
    """GradeHistory domain entity.

    Records grade corrections for audit purposes.
    Each correction creates a new history entry preserving the previous value.
    """

    def __init__(
        self,
        id: int | None,
        result_id: int,
        previous_score: float | None,
        new_score: float | None,
        previous_pass_fail: str,
        new_pass_fail: str,
        corrected_by: int | None = None,
        reason: str = "",
        corrected_at: datetime | None = None,
    ):
        self.id = id
        self.result_id = result_id
        self.previous_score = previous_score
        self.new_score = new_score
        self.previous_pass_fail = previous_pass_fail
        self.new_pass_fail = new_pass_fail
        self.corrected_by = corrected_by
        self.reason = reason
        self.corrected_at = corrected_at or datetime.now()

    def __repr__(self) -> str:
        return (
            f"<GradeHistory id={self.id} result={self.result_id} "
            f"prev={self.previous_score} new={self.new_score}>"
        )
