"""Portal service — aggregates data for role-specific dashboards."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date as date_type
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.application.assessment import assessment_service
from app.application.attendance import attendance_service
from app.application.enrollment import enrollment_service
from app.application.finance import finance_service
from app.extensions import db
from app.infrastructure.database.models import (
    AcademyClassModel,
    AssessmentModel,
    AssessmentResultModel,
    AttendanceModel,
    CourseModel,
    EnrollmentModel,
    FinancialTransactionModel,
    SessionModel,
    UserModel,
    user_roles,
)

logger = logging.getLogger(__name__)

# Class statuses that count as operational ("active") for dashboard purposes:
# PLANNED classes accept enrollments and generate sessions; ACTIVE classes are
# running. COMPLETED/CANCELLED classes are historical and excluded.
OPERATIONAL_CLASS_STATUSES = ("PLANNED", "ACTIVE")

# Assessment statuses that need administrator/teacher follow-up: OPEN exams are
# in progress, CLOSED exams await grading/publication.
ATTENTION_ASSESSMENT_STATUSES = ("OPEN", "CLOSED")

# How far back the "new students" KPI looks.
NEW_STUDENT_WINDOW_DAYS = 30

# Number of calendar months (including the current one) in trend charts.
TREND_MONTHS = 6


def _count_by_model(model: db.Model, **filters: Any) -> int:
    """Count rows in a table with optional filters."""
    return (
        db.session.query(func.count()).select_from(model).filter_by(**filters).scalar()
        or 0
    )


def _count_active_users_in_role(role_name: str) -> int:
    """Count active users holding a given role (role/profile-specific)."""
    return (
        db.session.query(func.count(func.distinct(UserModel.id)))
        .select_from(UserModel)
        .join(user_roles, user_roles.c.user_id == UserModel.id)
        .filter(
            user_roles.c.role_name == role_name,
            UserModel.is_active_user.is_(True),
        )
        .scalar()
        or 0
    )


def _optional(label: str, fn: Callable[[], Any]) -> Any | None:
    """Run an optional dashboard section, returning None (not zero) on failure.

    Optional sections (trends, today's schedule, debtor ranking) must never
    turn the whole dashboard into a 500 error and must never silently render
    as plausible-looking zeros. The template renders an error state for None.
    """
    try:
        return fn()
    except Exception:  # noqa: BLE001 — dashboard resilience boundary
        logger.exception("Admin dashboard optional section failed: %s", label)
        return None


# ---------------------------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------------------------


def get_admin_dashboard() -> dict[str, Any]:
    """Build data for admin dashboard.

    Metric definitions (see docs/ADMIN_DASHBOARD.md):
      - active_students: users with STUDENT role and is_active_user=True.
      - new_students: active students created within NEW_STUDENT_WINDOW_DAYS.
      - active_teachers: users with TEACHER role and is_active_user=True.
      - active_classes: classes with status PLANNED or ACTIVE.
      - upcoming_classes: operational classes with start_date after today.
      - distinct_courses: rows in the courses table.
      - approved_enrollments / pending_enrollments: enrollments by status.
      - approved_students: distinct students with an APPROVED enrollment.
      - Finance figures reuse finance_service canonical definitions.
      - month boundaries are Gregorian calendar months, consistent with
        finance_service.get_dashboard_summary().

    Returns:
        Dictionary with aggregated stats for admin overview.
    """
    today = date_type.today()

    active_students = _count_active_users_in_role("STUDENT")
    active_teachers = _count_active_users_in_role("TEACHER")
    new_students = _count_new_students()

    active_classes = (
        db.session.query(func.count())
        .select_from(AcademyClassModel)
        .filter(AcademyClassModel.status.in_(OPERATIONAL_CLASS_STATUSES))
        .scalar()
        or 0
    )
    upcoming_classes = (
        db.session.query(func.count())
        .select_from(AcademyClassModel)
        .filter(
            AcademyClassModel.status.in_(OPERATIONAL_CLASS_STATUSES),
            AcademyClassModel.start_date > today,
        )
        .scalar()
        or 0
    )
    distinct_courses = _count_by_model(CourseModel)

    approved_enrollments = _count_by_model(EnrollmentModel, status="APPROVED")
    pending_enrollments = _count_by_model(EnrollmentModel, status="PENDING")
    approved_students = (
        db.session.query(func.count(func.distinct(EnrollmentModel.student_user_id)))
        .filter(EnrollmentModel.status == "APPROVED")
        .scalar()
        or 0
    )

    assessments_total = (
        db.session.query(func.count())
        .select_from(AssessmentModel)
        .filter(AssessmentModel.status != "CANCELLED")
        .scalar()
        or 0
    )
    assessments_attention = (
        db.session.query(func.count())
        .select_from(AssessmentModel)
        .filter(AssessmentModel.status.in_(ATTENTION_ASSESSMENT_STATUSES))
        .scalar()
        or 0
    )

    finance_summary = finance_service.get_dashboard_summary()
    finance_month = _month_net_collections(today)
    top_debtors = _optional("top_debtors", _get_top_debtors)
    collection_trend = _optional("collection_trend", _get_collection_trend)
    enrollment_trend = _optional("enrollment_trend", _get_enrollment_trend)
    today_overview = _optional("today_overview", lambda: _get_today_overview(today))

    recent_pending = (
        EnrollmentModel.query.options(
            joinedload(EnrollmentModel.student).joinedload(UserModel.student_profile),
            joinedload(EnrollmentModel.academy_class),
        )
        .filter(EnrollmentModel.status == "PENDING")
        .order_by(EnrollmentModel.requested_at.desc())
        .limit(5)
        .all()
    )

    recent_classes = (
        AcademyClassModel.query.order_by(AcademyClassModel.created_at.desc())
        .limit(5)
        .all()
    )

    academic_context = _get_academic_context()
    attention_items = _build_attention_items(
        pending_enrollments=pending_enrollments,
        finance_summary=finance_summary,
        assessments_attention=assessments_attention,
        today_overview=today_overview,
        active_classes=active_classes,
        active_students=active_students,
    )

    return {
        # Core KPIs
        "active_students": active_students,
        "new_students": new_students,
        "active_teachers": active_teachers,
        "active_classes": active_classes,
        "upcoming_classes": upcoming_classes,
        "distinct_courses": distinct_courses,
        "approved_enrollments": approved_enrollments,
        "pending_enrollments": pending_enrollments,
        "approved_students": approved_students,
        "assessments_total": assessments_total,
        "assessments_attention": assessments_attention,
        # Legacy keys kept for backward compatibility with existing templates.
        "total_students": active_students,
        "total_teachers": active_teachers,
        "total_classes": active_classes,
        "total_courses": distinct_courses,
        "total_enrollments": approved_enrollments,
        "total_assessments": assessments_total,
        "open_assessments": assessments_attention,
        # Finance
        "finance_summary": finance_summary,
        "finance_month": finance_month,
        "top_debtors": top_debtors,
        "collection_trend": collection_trend,
        "enrollment_trend": enrollment_trend,
        # Operations
        "today_overview": today_overview,
        "attention_items": attention_items,
        "academic_context": academic_context,
        "recent_enrollments": recent_pending,
        "recent_classes": recent_classes,
    }


def _count_new_students() -> int:
    """Count active students created within the recent window."""
    cutoff = datetime.now() - timedelta(days=NEW_STUDENT_WINDOW_DAYS)
    return (
        db.session.query(func.count(func.distinct(UserModel.id)))
        .select_from(UserModel)
        .join(user_roles, user_roles.c.user_id == UserModel.id)
        .filter(
            user_roles.c.role_name == "STUDENT",
            UserModel.is_active_user.is_(True),
            UserModel.created_at >= cutoff,
        )
        .scalar()
        or 0
    )


def _month_bounds(today: date_type) -> tuple[date_type, date_type]:
    """Return (first day of this Gregorian month, first day of next month)."""
    month_start = today.replace(day=1)
    if month_start.month == 12:
        next_start = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_start = month_start.replace(month=month_start.month + 1)
    return month_start, next_start


def _month_net_collections(today: date_type) -> dict[str, Any]:
    """Net collected cash for the current and previous Gregorian months.

    Uses the canonical finance_service.get_revenue_report definition
    (payments − refunds + signed reversals) so the dashboard never carries a
    second finance formula.
    """
    month_start, next_start = _month_bounds(today)
    prev_end = month_start - timedelta(days=1)
    prev_start = prev_end.replace(day=1)
    current = finance_service.get_revenue_report(
        start_date=month_start, end_date=next_start - timedelta(days=1)
    )
    previous = finance_service.get_revenue_report(
        start_date=prev_start, end_date=prev_end
    )
    return {
        "month_start": month_start,
        "prev_month_start": prev_start,
        "current_net": current["net_revenue"],
        "current_gross": current["payments"],
        "previous_net": previous["net_revenue"],
    }


def _get_top_debtors(limit: int = 5) -> list[dict[str, Any]]:
    """Return the largest debtor balances with display names (one query each)."""
    report = finance_service.get_debt_report()
    if not report:
        return []
    report.sort(key=lambda row: row["balance"])
    top = report[:limit]
    users = UserModel.query.filter(
        UserModel.id.in_([row["student_user_id"] for row in top])
    ).all()
    users_map = {u.id: u for u in users}
    result = []
    for row in top:
        user = users_map.get(row["student_user_id"])
        name = user.login if user else "—"
        if user is not None and user.student_profile is not None:
            name = f"{user.student_profile.first_name} {user.student_profile.last_name}"
        result.append(
            {
                "student_user_id": row["student_user_id"],
                "balance": row["balance"],
                "display_name": name,
            }
        )
    return result


def _get_collection_trend() -> list[dict[str, Any]]:
    """Gross collected payments per Gregorian month for the last TREND_MONTHS."""
    import jdatetime

    today = date_type.today()
    months: list[dict[str, Any]] = []
    year, month = today.year, today.month
    for _ in range(TREND_MONTHS):
        start = date_type(year, month, 1)
        if month == 12:
            end = date_type(year + 1, 1, 1)
        else:
            end = date_type(year, month + 1, 1)
        total = (
            db.session.query(
                func.coalesce(func.sum(FinancialTransactionModel.amount), 0)
            )
            .filter(
                FinancialTransactionModel.status == "ACTIVE",
                FinancialTransactionModel.transaction_type == "PAYMENT",
                FinancialTransactionModel.created_at
                >= datetime.combine(start, datetime.min.time()),
                FinancialTransactionModel.created_at
                < datetime.combine(end, datetime.min.time()),
            )
            .scalar()
        )
        jalali = jdatetime.date.fromgregorian(date=start)
        months.append(
            {
                "key": f"{start.year}-{start.month:02d}",
                "label": f"{jalali.year}/{jalali.month:02d}",
                "total": Decimal(str(total)),
            }
        )
        if month == 1:
            year, month = year - 1, 12
        else:
            month -= 1
    months.reverse()
    return months


def _get_enrollment_trend() -> list[dict[str, Any]]:
    """Approved enrollments per Gregorian month for the last TREND_MONTHS."""
    import jdatetime

    today = date_type.today()
    months: list[dict[str, Any]] = []
    year, month = today.year, today.month
    for _ in range(TREND_MONTHS):
        start = date_type(year, month, 1)
        if month == 12:
            end = date_type(year + 1, 1, 1)
        else:
            end = date_type(year, month + 1, 1)
        count = (
            db.session.query(func.count())
            .select_from(EnrollmentModel)
            .filter(
                EnrollmentModel.status == "APPROVED",
                EnrollmentModel.approved_at
                >= datetime.combine(start, datetime.min.time()),
                EnrollmentModel.approved_at
                < datetime.combine(end, datetime.min.time()),
            )
            .scalar()
            or 0
        )
        jalali = jdatetime.date.fromgregorian(date=start)
        months.append(
            {
                "key": f"{start.year}-{start.month:02d}",
                "label": f"{jalali.year}/{jalali.month:02d}",
                "total": count,
            }
        )
        if month == 1:
            year, month = year - 1, 12
        else:
            month -= 1
    months.reverse()
    return months


def _get_today_overview(today: date_type) -> dict[str, Any]:
    """Summarize today's sessions and their attendance-recording status.

    A session counts as recorded only when attendance rows exist for every
    approved enrollment — absence of records is never treated as presence.
    """
    sessions = (
        SessionModel.query.options(joinedload(SessionModel.academy_class))
        .filter(
            SessionModel.scheduled_date == today,
            SessionModel.status != "CANCELLED",
        )
        .order_by(SessionModel.start_time)
        .limit(20)
        .all()
    )
    items: list[dict[str, Any]] = []
    recorded_count = 0
    for session in sessions:
        eligible = (
            db.session.query(func.count())
            .select_from(EnrollmentModel)
            .filter(
                EnrollmentModel.class_id == session.class_id,
                EnrollmentModel.status == "APPROVED",
            )
            .scalar()
            or 0
        )
        recorded = (
            db.session.query(func.count(func.distinct(AttendanceModel.enrollment_id)))
            .join(
                EnrollmentModel,
                AttendanceModel.enrollment_id == EnrollmentModel.id,
            )
            .filter(
                AttendanceModel.session_id == session.id,
                EnrollmentModel.status == "APPROVED",
            )
            .scalar()
            or 0
        )
        is_recorded = eligible > 0 and recorded >= eligible
        if is_recorded:
            recorded_count += 1
        teacher_name = "—"
        academy_class = session.academy_class
        if academy_class is not None and academy_class.teacher is not None:
            profile = academy_class.teacher.teacher_profile
            if profile is not None:
                teacher_name = f"{profile.first_name} {profile.last_name}"
            else:
                teacher_name = academy_class.teacher.login
        items.append(
            {
                "session_id": session.id,
                "class_id": session.class_id,
                "class_title": academy_class.title if academy_class else "—",
                "session_number": session.session_number,
                "session_title": session.title or "",
                "start_time": session.start_time,
                "end_time": session.end_time,
                "status": session.status,
                "teacher_name": teacher_name,
                "eligible_count": eligible,
                "recorded_count": recorded,
                "is_recorded": is_recorded,
            }
        )
    total = len(items)
    return {
        "date": today,
        "sessions": items,
        "total": total,
        "recorded": recorded_count,
        # None when there is no denominator — the template shows an
        # explicit "no classes today" state instead of 0%.
        "completion_rate": (recorded_count / total) if total else None,
    }


def _get_academic_context() -> dict[str, Any]:
    """Return active academic year/semester titles (None when not configured)."""
    from app.infrastructure.database.models import AcademicYearModel, SemesterModel

    year = AcademicYearModel.query.filter_by(is_active=True).first()
    semester = SemesterModel.query.filter_by(is_active=True).first()
    return {
        "year_title": year.title if year else None,
        "semester_title": semester.title if semester else None,
    }


def _build_attention_items(
    *,
    pending_enrollments: int,
    finance_summary: dict[str, Any],
    assessments_attention: int,
    today_overview: dict[str, Any] | None,
    active_classes: int,
    active_students: int,
) -> list[dict[str, Any]]:
    """Build the prioritized actionable-exceptions list (real data only)."""
    items: list[dict[str, Any]] = []
    if pending_enrollments > 0:
        items.append(
            {
                "severity": "warning",
                "message": f"{pending_enrollments} درخواست ثبت‌نام در انتظار تأیید است.",
                "count": pending_enrollments,
                "endpoint": "enrollment.admin_pending_list",
                "action_label": "بررسی درخواست‌ها",
            }
        )
    debtors = int(finance_summary.get("debtors_count", 0) or 0)
    if debtors > 0:
        items.append(
            {
                "severity": "danger",
                "message": (
                    f"{debtors} دانش‌آموز بدهی تسویه‌نشده دارند. پیگیری لازم است."
                ),
                "count": debtors,
                "endpoint": "finance.admin_debt_report",
                "action_label": "مشاهده گزارش بدهکاران",
            }
        )
    if today_overview is not None:
        unrecorded = sum(1 for s in today_overview["sessions"] if not s["is_recorded"])
        if today_overview["total"] > 0 and unrecorded > 0:
            items.append(
                {
                    "severity": "warning",
                    "message": (
                        f"حضور و غیاب {unrecorded} جلسه امروز هنوز "
                        "به‌طور کامل ثبت نشده است."
                    ),
                    "count": unrecorded,
                    "endpoint": "attendance.admin_attendance_list",
                    "action_label": "ثبت حضور و غیاب",
                }
            )
    if assessments_attention > 0:
        items.append(
            {
                "severity": "info",
                "message": (
                    f"{assessments_attention} آزمون باز یا بسته‌شده "
                    "نیازمند پیگیری (برگزاری یا نمره‌گذاری) است."
                ),
                "count": assessments_attention,
                "endpoint": "assessment.admin_assessment_list",
                "action_label": "مشاهده آزمون‌ها",
            }
        )
    if active_students == 0 and active_classes == 0:
        items.append(
            {
                "severity": "info",
                "message": (
                    "هنوز دانش‌آموز یا کلاس فعالی ثبت نشده است. "
                    "از اقدامات سریع زیر شروع کنید."
                ),
                "count": 0,
                "endpoint": "admin.user_create",
                "action_label": "ایجاد کاربر",
            }
        )
    return items


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
