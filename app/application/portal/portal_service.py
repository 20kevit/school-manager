"""Portal service — aggregates data for role-specific dashboards."""

from __future__ import annotations

from datetime import date as date_type
from typing import Any

from sqlalchemy import func

from app.application.assessment import assessment_service
from app.application.attendance import attendance_service
from app.application.enrollment import enrollment_service
from app.application.finance import finance_service
from app.extensions import db
from app.infrastructure.database.models import (
    AcademyClassModel,
    AssessmentModel,
    AssessmentResultModel,
    EnrollmentModel,
    UserModel,
)


def _count_by_model(model: db.Model, **filters: Any) -> int:
    """Count rows in a table with optional filters."""
    return (
        db.session.query(func.count()).select_from(model).filter_by(**filters).scalar()
        or 0
    )


# ---------------------------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------------------------


def get_admin_dashboard() -> dict[str, Any]:
    """Build data for admin dashboard.

    Returns:
        Dictionary with aggregated stats for admin overview.
    """
    total_students = _count_by_model(UserModel) - _count_by_model(
        UserModel, is_active_user=False
    )
    total_teachers = _count_by_model(UserModel)
    total_classes = _count_by_model(AcademyClassModel)
    total_courses = _count_by_model(AcademyClassModel)  # distinct courses from classes
    total_enrollments = _count_by_model(EnrollmentModel, status="APPROVED")
    pending_enrollments = _count_by_model(EnrollmentModel, status="PENDING")
    total_assessments = _count_by_model(AssessmentModel)
    open_assessments = _count_by_model(AssessmentModel, status="OPEN")

    finance_summary = finance_service.get_dashboard_summary()

    recent_enrollments = (
        EnrollmentModel.query.filter(EnrollmentModel.status == "PENDING")
        .order_by(EnrollmentModel.requested_at.desc())
        .limit(5)
        .all()
    )

    recent_classes = (
        AcademyClassModel.query.order_by(AcademyClassModel.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_classes": total_classes,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "pending_enrollments": pending_enrollments,
        "total_assessments": total_assessments,
        "open_assessments": open_assessments,
        "finance_summary": finance_summary,
        "recent_enrollments": recent_enrollments,
        "recent_classes": recent_classes,
    }


# ---------------------------------------------------------------------------
# Teacher Dashboard
# ---------------------------------------------------------------------------


def get_teacher_dashboard(teacher_user_id: int) -> dict[str, Any]:
    """Build data for teacher dashboard.

    Args:
        teacher_user_id: The teacher's user ID.

    Returns:
        Dictionary with aggregated stats for teacher overview.
    """
    classes = (
        AcademyClassModel.query.filter_by(teacher_user_id=teacher_user_id)
        .order_by(AcademyClassModel.created_at.desc())
        .all()
    )

    class_summaries: list[dict[str, Any]] = []
    for cls in classes:
        summary = assessment_service.get_class_academic_summary(cls.id)
        summary["class"] = cls
        class_summaries.append(summary)

    # Count unique students across teacher's classes
    teacher_student_ids: set[int] = set()
    for cls in classes:
        enrollments = EnrollmentModel.query.filter_by(
            class_id=cls.id, status="APPROVED"
        ).all()
        for e in enrollments:
            teacher_student_ids.add(e.student_user_id)

    pending_grades_count = AssessmentModel.query.filter(
        AssessmentModel.class_id.in_([cls.id for cls in classes]) if classes else False,
        AssessmentModel.status == "GRADED",
    ).count()

    return {
        "classes": classes,
        "class_summaries": class_summaries,
        "total_students": len(teacher_student_ids),
        "total_classes": len(classes),
        "pending_grades_count": pending_grades_count,
    }


# ---------------------------------------------------------------------------
# Student Dashboard
# ---------------------------------------------------------------------------


def get_student_dashboard(student_user_id: int) -> dict[str, Any]:
    """Build data for student dashboard.

    Args:
        student_user_id: The student's user ID.

    Returns:
        Dictionary with aggregated stats for student overview.
    """
    enrollments = enrollment_service.list_enrollments_by_student(student_user_id)
    active_enrollments = [e for e in enrollments if e.status == "APPROVED"]

    academic_summary = assessment_service.get_student_academic_summary(student_user_id)
    attendance_summary = attendance_service.compute_student_summary(student_user_id)

    can_see_finance = _is_student_adult(student_user_id)
    finance_balance = None
    if can_see_finance:
        finance_balance = finance_service.get_student_balance(student_user_id)

    recent_results = (
        AssessmentResultModel.query.filter_by(student_user_id=student_user_id)
        .order_by(AssessmentResultModel.graded_at.desc())
        .limit(5)
        .all()
    )

    return {
        "enrollments": enrollments,
        "active_enrollments": active_enrollments,
        "academic_summary": academic_summary,
        "attendance_summary": attendance_summary,
        "can_see_finance": can_see_finance,
        "finance_balance": finance_balance,
        "recent_results": recent_results,
    }


# ---------------------------------------------------------------------------
# Parent Dashboard
# ---------------------------------------------------------------------------


def get_parent_dashboard(parent_user_id: int) -> dict[str, Any]:
    """Build data for parent dashboard.

    Args:
        parent_user_id: The parent's user ID.

    Returns:
        Dictionary with aggregated stats for parent overview.
    """
    children = assessment_service.get_parent_children(parent_user_id)

    children_data: list[dict[str, Any]] = []
    for child in children:
        academic_summary = assessment_service.get_student_academic_summary(child.id)
        attendance_summary = attendance_service.compute_student_summary(child.id)

        can_see_finance = _is_student_adult(child.id)
        finance_balance = None
        if can_see_finance:
            finance_balance = finance_service.get_student_balance(child.id)

        children_data.append(
            {
                "user": child,
                "academic_summary": academic_summary,
                "attendance_summary": attendance_summary,
                "can_see_finance": can_see_finance,
                "finance_balance": finance_balance,
            }
        )

    return {
        "children": children,
        "children_data": children_data,
        "total_children": len(children),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_student_adult(student_user_id: int) -> bool:
    """Check if a student is 18 or older."""
    from app.infrastructure.database.models import StudentProfileModel

    profile = StudentProfileModel.query.filter_by(user_id=student_user_id).first()
    if profile is None:
        return False

    today = date_type.today()
    age = (
        today.year
        - profile.birth_date.year
        - (
            (today.month, today.day)
            < (profile.birth_date.month, profile.birth_date.day)
        )
    )
    return age >= 18
