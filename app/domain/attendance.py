from __future__ import annotations

from datetime import datetime
from enum import StrEnum


class AttendanceStatus(StrEnum):
    """Status of an attendance record."""

    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    EXCUSED = "EXCUSED"


class Attendance:
    """Attendance domain entity.

    Represents a student's attendance for a specific session.
    Linked via an Enrollment (student must be enrolled in the session's class).
    """

    def __init__(
        self,
        id: int | None,
        enrollment_id: int,
        session_id: int,
        status: AttendanceStatus,
        note: str = "",
        recorded_at: datetime | None = None,
        updated_at: datetime | None = None,
        recorded_by: int | None = None,
    ):
        self.id = id
        self.enrollment_id = enrollment_id
        self.session_id = session_id
        self.status = status
        self.note = note
        self.recorded_at = recorded_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.recorded_by = recorded_by

    def __repr__(self) -> str:
        return (
            f"<Attendance id={self.id} enrollment={self.enrollment_id} "
            f"session={self.session_id} status={self.status}>"
        )
