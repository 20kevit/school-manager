from __future__ import annotations

from datetime import datetime
from enum import StrEnum


class EnrollmentStatus(StrEnum):
    """Status of an enrollment request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class Enrollment:
    """Enrollment domain entity.

    Represents a student's participation in a specific class.
    """

    def __init__(
        self,
        id: int | None,
        student_user_id: int,
        class_id: int,
        status: EnrollmentStatus = EnrollmentStatus.PENDING,
        requested_at: datetime | None = None,
        approved_at: datetime | None = None,
        rejected_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.student_user_id = student_user_id
        self.class_id = class_id
        self.status = status
        self.requested_at = requested_at or datetime.now()
        self.approved_at = approved_at
        self.rejected_at = rejected_at
        self.cancelled_at = cancelled_at
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def can_transition_to(self, new_status: EnrollmentStatus) -> bool:
        """Check if a status transition is valid."""
        valid_transitions = {
            EnrollmentStatus.PENDING: {
                EnrollmentStatus.APPROVED,
                EnrollmentStatus.REJECTED,
                EnrollmentStatus.CANCELLED,
            },
            EnrollmentStatus.APPROVED: {
                EnrollmentStatus.CANCELLED,
            },
        }
        return new_status in valid_transitions.get(self.status, set())

    def __repr__(self) -> str:
        return (
            f"<Enrollment id={self.id} student={self.student_user_id} "
            f"class={self.class_id} status={self.status}>"
        )
