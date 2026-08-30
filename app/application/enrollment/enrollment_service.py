from __future__ import annotations

from datetime import datetime

from app.extensions import db
from app.infrastructure.database.models import (
    AcademyClassModel,
    EnrollmentModel,
    StudentProfileModel,
    UserModel,
)

# Finance integration imported lazily to avoid circular imports
# at module level.  Calls use the full path when needed.


class EnrollmentError(Exception):
    """Raised when an enrollment operation fails."""


def request_enrollment(
    student_user_id: int,
    class_id: int,
) -> EnrollmentModel:
    """Student requests enrollment in a class.

    Creates a PENDING enrollment request.
    """
    student = UserModel.query.get(student_user_id)
    if student is None:
        raise EnrollmentError("Student not found.")

    if not student.has_role("STUDENT"):
        raise EnrollmentError("User is not a student.")

    profile = StudentProfileModel.query.filter_by(user_id=student_user_id).first()
    if profile is None:
        raise EnrollmentError("Student profile not found.")

    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        raise EnrollmentError("Class not found.")

    if academy_class.status in ("CANCELLED", "COMPLETED"):
        raise EnrollmentError("Class is not accepting enrollments.")

    existing_active = _get_active_enrollment(student_user_id, class_id)
    if existing_active is not None:
        raise EnrollmentError("Student is already enrolled or has a pending request.")

    enrollment = EnrollmentModel(
        student_user_id=student_user_id,
        class_id=class_id,
        status="PENDING",
        requested_at=datetime.now(),
    )
    db.session.add(enrollment)
    db.session.commit()
    return enrollment


def admin_enroll_student(
    student_user_id: int,
    class_id: int,
    auto_approve: bool = True,
) -> EnrollmentModel:
    """Admin directly enrolls a student in a class.

    If auto_approve is True, enrollment becomes APPROVED immediately
    and tuition charge is created.
    """
    student = UserModel.query.get(student_user_id)
    if student is None:
        raise EnrollmentError("Student not found.")

    if not student.has_role("STUDENT"):
        raise EnrollmentError("User is not a student.")

    profile = StudentProfileModel.query.filter_by(user_id=student_user_id).first()
    if profile is None:
        raise EnrollmentError("Student profile not found.")

    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        raise EnrollmentError("Class not found.")

    if academy_class.status in ("CANCELLED", "COMPLETED"):
        raise EnrollmentError("Class is not accepting enrollments.")

    existing_active = _get_active_enrollment(student_user_id, class_id)
    if existing_active is not None:
        raise EnrollmentError("Student is already enrolled or has a pending request.")

    now = datetime.now()
    status = "APPROVED" if auto_approve else "PENDING"

    enrollment = EnrollmentModel(
        student_user_id=student_user_id,
        class_id=class_id,
        status=status,
        requested_at=now,
        approved_at=now if auto_approve else None,
    )
    db.session.add(enrollment)
    db.session.commit()

    # Finance integration: create tuition charge on auto-approve
    if auto_approve:
        from app.application.finance import finance_service

        try:
            finance_service.on_enrollment_approved(enrollment)
        except finance_service.FinanceError:
            pass  # Tuition charge may fail if class has no tuition set

    return enrollment


def approve_enrollment(enrollment: EnrollmentModel) -> EnrollmentModel:
    """Approve a pending enrollment request.

    Re-checks class availability, capacity, and duplicate enrollment.
    Automatically creates tuition charge via finance service.
    """
    if enrollment.status != "PENDING":
        raise EnrollmentError("Only pending enrollments can be approved.")

    academy_class = AcademyClassModel.query.get(enrollment.class_id)
    if academy_class is None:
        raise EnrollmentError("Class not found.")

    if academy_class.status in ("CANCELLED", "COMPLETED"):
        raise EnrollmentError("Class is not accepting enrollments.")

    approved_count = _count_approved_enrollments(enrollment.class_id)
    if approved_count >= academy_class.capacity:
        raise EnrollmentError("Class is at full capacity.")

    existing_active = _get_active_enrollment(
        enrollment.student_user_id, enrollment.class_id, exclude_id=enrollment.id
    )
    if existing_active is not None:
        raise EnrollmentError("Student already has an active enrollment in this class.")

    enrollment.status = "APPROVED"
    enrollment.approved_at = datetime.now()
    db.session.commit()

    # Finance integration: create tuition charge
    from app.application.finance import finance_service

    try:
        finance_service.on_enrollment_approved(enrollment)
    except finance_service.FinanceError:
        pass  # Tuition charge may fail if class has no tuition set

    return enrollment


def reject_enrollment(enrollment: EnrollmentModel) -> EnrollmentModel:
    """Reject a pending enrollment request."""
    if enrollment.status != "PENDING":
        raise EnrollmentError("Only pending enrollments can be rejected.")

    enrollment.status = "REJECTED"
    enrollment.rejected_at = datetime.now()
    db.session.commit()
    return enrollment


def cancel_enrollment(enrollment: EnrollmentModel) -> EnrollmentModel:
    """Cancel an enrollment (approved or pending).

    Creates financial reversal for approved enrollments.
    """
    if enrollment.status not in ("PENDING", "APPROVED"):
        raise EnrollmentError("Only pending or approved enrollments can be cancelled.")

    was_approved = enrollment.status == "APPROVED"
    enrollment.status = "CANCELLED"
    enrollment.cancelled_at = datetime.now()
    db.session.commit()

    # Finance integration: create reversal for approved enrollments
    if was_approved:
        from app.application.finance import finance_service

        try:
            finance_service.on_enrollment_cancelled(enrollment)
        except finance_service.FinanceError:
            pass  # Reversal may fail if no tuition charge exists

    return enrollment


def get_enrollment(enrollment_id: int) -> EnrollmentModel | None:
    """Get an enrollment by ID."""
    return EnrollmentModel.query.get(enrollment_id)


def list_enrollments_by_student(student_user_id: int) -> list[EnrollmentModel]:
    """List all enrollments for a student."""
    return (
        EnrollmentModel.query.filter_by(student_user_id=student_user_id)
        .order_by(EnrollmentModel.created_at.desc())
        .all()
    )


def list_enrollments_by_class(class_id: int) -> list[EnrollmentModel]:
    """List all enrollments for a class."""
    return (
        EnrollmentModel.query.filter_by(class_id=class_id)
        .order_by(EnrollmentModel.created_at.desc())
        .all()
    )


def list_pending_enrollments_by_class(class_id: int) -> list[EnrollmentModel]:
    """List pending enrollments for a class."""
    return (
        EnrollmentModel.query.filter_by(class_id=class_id, status="PENDING")
        .order_by(EnrollmentModel.requested_at)
        .all()
    )


def list_all_pending_enrollments() -> list[EnrollmentModel]:
    """List all pending enrollments across all classes."""
    return (
        EnrollmentModel.query.filter_by(status="PENDING")
        .order_by(EnrollmentModel.requested_at)
        .all()
    )


def count_approved_enrollments(class_id: int) -> int:
    """Count approved enrollments for a class."""
    return _count_approved_enrollments(class_id)


def get_class_available_capacity(academy_class: AcademyClassModel) -> int:
    """Get remaining capacity for a class."""
    approved_count = _count_approved_enrollments(academy_class.id)
    return max(0, academy_class.capacity - approved_count)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_active_enrollment(
    student_user_id: int,
    class_id: int,
    exclude_id: int | None = None,
) -> EnrollmentModel | None:
    """Get an active enrollment (PENDING or APPROVED) for a student in a class."""
    query = EnrollmentModel.query.filter(
        EnrollmentModel.student_user_id == student_user_id,
        EnrollmentModel.class_id == class_id,
        EnrollmentModel.status.in_(["PENDING", "APPROVED"]),
    )
    if exclude_id is not None:
        query = query.filter(EnrollmentModel.id != exclude_id)
    return query.first()


def _count_approved_enrollments(class_id: int) -> int:
    """Count approved enrollments for a class."""
    return EnrollmentModel.query.filter_by(class_id=class_id, status="APPROVED").count()
