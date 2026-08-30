from __future__ import annotations

from datetime import datetime

from app.extensions import db
from app.infrastructure.database.models import (
    AcademyClassModel,
    AttendanceModel,
    EnrollmentModel,
    SessionModel,
)

VALID_STATUSES = {"PRESENT", "ABSENT", "LATE", "EXCUSED"}


class AttendanceError(Exception):
    """Raised when an attendance operation fails."""


def record_attendance(
    enrollment_id: int,
    session_id: int,
    status: str,
    note: str = "",
    recorded_by: int | None = None,
) -> AttendanceModel:
    """Record or update attendance for one student in one session.

    If an attendance record already exists for this enrollment+session,
    it is updated (not duplicated).
    """
    if status not in VALID_STATUSES:
        raise AttendanceError(f"Invalid status: {status}")

    enrollment = EnrollmentModel.query.get(enrollment_id)
    if enrollment is None:
        raise AttendanceError("Enrollment not found.")

    session = SessionModel.query.get(session_id)
    if session is None:
        raise AttendanceError("Session not found.")

    if enrollment.class_id != session.class_id:
        raise AttendanceError("Enrollment and session do not belong to the same class.")

    if enrollment.status != "APPROVED":
        raise AttendanceError(
            "Attendance can only be recorded for approved enrollments."
        )

    existing = AttendanceModel.query.filter_by(
        enrollment_id=enrollment_id,
        session_id=session_id,
    ).first()

    now = datetime.now()

    if existing is not None:
        existing.status = status
        existing.note = note
        existing.updated_at = now
        if recorded_by is not None:
            existing.recorded_by = recorded_by
        db.session.commit()
        return existing

    attendance = AttendanceModel(
        enrollment_id=enrollment_id,
        session_id=session_id,
        status=status,
        note=note,
        recorded_at=now,
        updated_at=now,
        recorded_by=recorded_by,
    )
    db.session.add(attendance)
    db.session.commit()
    return attendance


def record_session_attendance(
    session_id: int,
    attendance_data: list[dict],
    recorded_by: int | None = None,
) -> list[AttendanceModel]:
    """Bulk record attendance for an entire session.

    Args:
        session_id: The session to record attendance for.
        attendance_data: List of dicts with keys: enrollment_id, status, note (optional).
        recorded_by: User ID of the recorder.

    Returns:
        List of created/updated AttendanceModel records.
    """
    session = SessionModel.query.get(session_id)
    if session is None:
        raise AttendanceError("Session not found.")

    results = []
    for item in attendance_data:
        enrollment_id = item.get("enrollment_id")
        status = item.get("status", "")
        note = item.get("note", "")

        if enrollment_id is None or status not in VALID_STATUSES:
            raise AttendanceError(
                f"Invalid attendance data: enrollment_id={enrollment_id}, status={status}"
            )

        attendance = record_attendance(
            enrollment_id=enrollment_id,
            session_id=session_id,
            status=status,
            note=note,
            recorded_by=recorded_by,
        )
        results.append(attendance)

    return results


def get_session_attendance(session_id: int) -> list[AttendanceModel]:
    """Get all attendance records for a session."""
    return (
        AttendanceModel.query.filter_by(session_id=session_id)
        .order_by(AttendanceModel.id)
        .all()
    )


def get_attendance(attendance_id: int) -> AttendanceModel | None:
    """Get a single attendance record by ID."""
    return AttendanceModel.query.get(attendance_id)


def get_student_attendance(student_user_id: int) -> list[AttendanceModel]:
    """Get all attendance records for a student across all classes."""
    return (
        AttendanceModel.query.join(
            EnrollmentModel,
            AttendanceModel.enrollment_id == EnrollmentModel.id,
        )
        .filter(EnrollmentModel.student_user_id == student_user_id)
        .order_by(AttendanceModel.recorded_at.desc())
        .all()
    )


def get_attendance_by_enrollment(enrollment_id: int) -> list[AttendanceModel]:
    """Get all attendance records for a specific enrollment."""
    return (
        AttendanceModel.query.filter_by(enrollment_id=enrollment_id)
        .order_by(AttendanceModel.recorded_at)
        .all()
    )


def get_eligible_enrollments(session_id: int) -> list[EnrollmentModel]:
    """Get all approved enrollments for a session's class.

    These are the students eligible to have attendance recorded.
    """
    session = SessionModel.query.get(session_id)
    if session is None:
        raise AttendanceError("Session not found.")

    return (
        EnrollmentModel.query.filter_by(
            class_id=session.class_id,
            status="APPROVED",
        )
        .order_by(EnrollmentModel.id)
        .all()
    )


def compute_session_summary(session_id: int) -> dict:
    """Compute attendance summary for a session.

    Returns dict with counts per status and total.
    """
    records = get_session_attendance(session_id)
    summary = {"PRESENT": 0, "ABSENT": 0, "LATE": 0, "EXCUSED": 0, "total": 0}
    for r in records:
        if r.status in summary:
            summary[r.status] += 1
        summary["total"] += 1
    return summary


def compute_student_summary(student_user_id: int) -> dict:
    """Compute overall attendance summary for a student.

    Returns dict with counts per status and total.
    """
    records = get_student_attendance(student_user_id)
    summary = {"PRESENT": 0, "ABSENT": 0, "LATE": 0, "EXCUSED": 0, "total": 0}
    for r in records:
        if r.status in summary:
            summary[r.status] += 1
        summary["total"] += 1
    return summary


def is_teacher_of_class(teacher_user_id: int, class_id: int) -> bool:
    """Check if a teacher is assigned to a class."""
    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        return False
    return academy_class.teacher_user_id == teacher_user_id
