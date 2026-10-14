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
    SessionModel,
    UserModel,
    user_roles,
)

logger = logging.getLogger(__name__)

# Class statuses that count as operational ("active") for dashboard purposes:
# PLANNED classes accept enrollments and generate sessions; ACTIVE classes are
# running. COMPLETED/CANCELLED classes are historical and excluded.
OPERATIONAL_CLASS_STATUSES = ("PLANNED", "ACTIVE")

# Assessment attention is split into OPEN (in progress) and CLOSED (awaiting
# grading) counts with exact filtered destinations; no combined constant.

# How far back the "new students" KPI looks.
NEW_STUDENT_WINDOW_DAYS = 30

# Number of calendar months (including the current one) in trend charts.
TREND_MONTHS = 12

# Operational classes at or above this fill ratio trigger a capacity
# attention item (approvals can never exceed capacity, so near-full classes
# need planning attention before they close).
FULL_CAPACITY_THRESHOLD = 0.9

# Days (including today) covered by the attendance week chart.
ATTENDANCE_WEEK_DAYS = 7

# Persian month names for chart tick labels (Jalali month number -> name).
JALALI_MONTH_NAMES = {
    1: "فروردین",
    2: "اردیبهشت",
    3: "خرداد",
    4: "تیر",
    5: "مرداد",
    6: "شهریور",
    7: "مهر",
    8: "آبان",
    9: "آذر",
    10: "دی",
    11: "بهمن",
    12: "اسفند",
}

# Persian weekday names for the attendance week chart (Monday=0 .. Sunday=6).
WEEKDAY_NAMES_FA = {
    0: "دوشنبه",
    1: "سه‌شنبه",
    2: "چهارشنبه",
    3: "پنجشنبه",
    4: "جمعه",
    5: "شنبه",
    6: "یکشنبه",
}


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
      - running_classes: classes with status ACTIVE (currently running).
      - planned_classes: classes with status PLANNED (accepting enrollment).
      - upcoming_classes: operational (PLANNED/ACTIVE) classes with
        start_date after today.
      - distinct_courses: rows in the courses table.
      - approved_enrollments / pending_enrollments: enrollments by status.
      - approved_students: distinct students with an APPROVED enrollment.
      - Finance figures reuse finance_service canonical definitions;
        monthly buckets come from get_monthly_revenue() (same net formula).
      - month boundaries are Gregorian calendar months, consistent with
        finance_service.get_dashboard_summary().

    Returns:
        Dictionary with aggregated stats for admin overview.
    """
    today = date_type.today()

    active_students = _count_active_users_in_role("STUDENT")
    active_teachers = _count_active_users_in_role("TEACHER")
    new_students = _count_new_students()

    running_classes = _count_by_model(AcademyClassModel, status="ACTIVE")
    planned_classes = _count_by_model(AcademyClassModel, status="PLANNED")
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
    open_assessments = _count_by_model(AssessmentModel, status="OPEN")
    closed_assessments = _count_by_model(AssessmentModel, status="CLOSED")

    finance_summary = finance_service.get_dashboard_summary()
    monthly_revenue = _optional("monthly_revenue", _get_monthly_revenue)
    finance_month = _derive_finance_month(monthly_revenue)
    collections_chart = _build_collections_chart(monthly_revenue)
    top_debtors = _optional("top_debtors", _get_top_debtors)
    enrollment_trend = _optional("enrollment_trend", _get_enrollment_trend)
    enrollments_chart = _build_enrollments_chart(enrollment_trend)
    today_overview = _optional("today_overview", lambda: _get_today_overview(today))
    attendance_week = _optional("attendance_week", lambda: _get_attendance_week(today))
    attendance_chart = _build_attendance_chart(attendance_week)
    capacity_watch = _optional("capacity_watch", _get_capacity_watch)

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

    academic_context = _get_academic_context()
    attention_items = _build_attention_items(
        pending_enrollments=pending_enrollments,
        finance_summary=finance_summary,
        open_assessments=open_assessments,
        closed_assessments=closed_assessments,
        today_overview=today_overview,
        capacity_watch=capacity_watch,
        running_classes=running_classes,
        active_students=active_students,
    )

    return {
        # Core KPIs
        "active_students": active_students,
        "new_students": new_students,
        "active_teachers": active_teachers,
        "running_classes": running_classes,
        "planned_classes": planned_classes,
        "upcoming_classes": upcoming_classes,
        "distinct_courses": distinct_courses,
        "approved_enrollments": approved_enrollments,
        "pending_enrollments": pending_enrollments,
        "approved_students": approved_students,
        "assessments_total": assessments_total,
        "open_assessments": open_assessments,
        "closed_assessments": closed_assessments,
        # Finance
        "finance_summary": finance_summary,
        "finance_month": finance_month,
        "collections_chart": collections_chart,
        "top_debtors": top_debtors,
        "enrollments_chart": enrollments_chart,
        # Operations
        "today_overview": today_overview,
        "attendance_chart": attendance_chart,
        "capacity_watch": capacity_watch,
        "attention_items": attention_items,
        "academic_context": academic_context,
        "recent_enrollments": recent_pending,
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


def _month_starts(first_month: date_type, months: int) -> list[date_type]:
    """Return first-of-month Gregorian dates, oldest-first, ending this month."""
    year, month = first_month.year, first_month.month
    starts: list[date_type] = []
    for _ in range(months):
        starts.append(date_type(year, month, 1))
        if month == 1:
            year, month = year - 1, 12
        else:
            month -= 1
    starts.reverse()
    return starts


def _jalali_month_label(start: date_type) -> str:
    """Return a short Persian month label (e.g. 'مهر ۱۴۰۵') for a Gregorian month."""
    import jdatetime

    jalali = jdatetime.date.fromgregorian(date=start)
    return f"{JALALI_MONTH_NAMES[jalali.month]} {jalali.year}"


def _get_monthly_revenue() -> list[dict[str, Any]]:
    """Twelve monthly collection buckets with Jalali labels for charts.

    Single canonical query via finance_service.get_monthly_revenue(); net
    keeps the canonical payments − refunds + signed reversals definition.
    """
    today = date_type.today()
    first = _month_starts(today, TREND_MONTHS)[0]
    buckets = finance_service.get_monthly_revenue(first, TREND_MONTHS)
    for bucket in buckets:
        bucket["label"] = _jalali_month_label(bucket["start"])
    return buckets


def _derive_finance_month(
    monthly_revenue: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Derive current/previous month figures from the canonical buckets.

    Falls back to direct get_revenue_report() calls when the optional trend
    section failed, so the KPI never depends on chart availability.
    """
    if monthly_revenue:
        current = monthly_revenue[-1]
        previous = monthly_revenue[-2] if len(monthly_revenue) > 1 else None
        return {
            "month_start": current["start"],
            "prev_month_start": previous["start"] if previous else None,
            "current_net": current["net"],
            "current_gross": current["gross"],
            "previous_net": previous["net"] if previous else Decimal("0"),
        }
    today = date_type.today()
    month_start = today.replace(day=1)
    prev_end = month_start - timedelta(days=1)
    prev_start = prev_end.replace(day=1)
    current = finance_service.get_revenue_report(start_date=month_start)
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


def _get_enrollment_trend() -> list[dict[str, Any]]:
    """Twelve monthly buckets of requests vs approvals (single query).

    - requested: rows whose requested_at falls in the bucket month.
    - approved: rows with status APPROVED whose approved_at falls in the
      bucket month. Rows with NULL approved_at are excluded — approval date
      is never inferred from creation date.
    Both series are operational monthly counts, not a cohort conversion rate.
    """
    today = date_type.today()
    starts = _month_starts(today, TREND_MONTHS)
    terms = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else _next_month_start(start)
        terms.append(
            func.count(
                db.case(
                    (
                        db.and_(
                            EnrollmentModel.requested_at
                            >= datetime.combine(start, datetime.min.time()),
                            EnrollmentModel.requested_at
                            < datetime.combine(end, datetime.min.time()),
                        ),
                        1,
                    ),
                    else_=None,
                )
            ).label(f"requested_{i}")
        )
        terms.append(
            func.count(
                db.case(
                    (
                        db.and_(
                            EnrollmentModel.status == "APPROVED",
                            EnrollmentModel.approved_at
                            >= datetime.combine(start, datetime.min.time()),
                            EnrollmentModel.approved_at
                            < datetime.combine(end, datetime.min.time()),
                        ),
                        1,
                    ),
                    else_=None,
                )
            ).label(f"approved_{i}")
        )
    row = db.session.query(*terms).select_from(EnrollmentModel).one()
    buckets = []
    for i, start in enumerate(starts):
        buckets.append(
            {
                "key": f"{start.year}-{start.month:02d}",
                "label": _jalali_month_label(start),
                "requested": int(row[i * 2] or 0),
                "approved": int(row[i * 2 + 1] or 0),
            }
        )
    return buckets


def _next_month_start(start: date_type) -> date_type:
    """Return the first day of the month after the given first-of-month."""
    if start.month == 12:
        return date_type(start.year + 1, 1, 1)
    return date_type(start.year, start.month + 1, 1)


def _nice_ceiling(value: float) -> float:
    """Round up to a 1/2/2.5/5×10^n axis maximum (never zero)."""
    import math

    if value <= 0:
        return 1.0
    exp = 10 ** math.floor(math.log10(value))
    for mult in (1, 2, 2.5, 5, 10):
        if mult * exp >= value:
            return float(mult * exp)
    return float(10 * exp)


def _axis_ticks(y_max: float) -> list[float]:
    """Return five evenly spaced axis ticks from 0 to y_max."""
    return [y_max * f for f in (0, 0.25, 0.5, 0.75, 1.0)]


def _build_collections_chart(
    monthly_revenue: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """Chart model for monthly collections (net bars + gross line).

    Net is the principal series (canonical definition); gross is a clearly
    labeled secondary series. Values stay Decimal; the template formats.
    """
    if not monthly_revenue:
        return None
    peak = max(
        [float(b["gross"]) for b in monthly_revenue]
        + [float(b["net"]) for b in monthly_revenue]
    )
    if peak <= 0:
        # Genuinely empty ledger: a flat zero line on a 0–1 axis rather
        # than fractional-Toman gridlines.
        y_max, ticks = 1.0, [0.0, 1.0]
    else:
        y_max, ticks = _nice_ceiling(peak), _axis_ticks(_nice_ceiling(peak))
    return {
        "points": [
            {
                "key": b["key"],
                "label": b["label"],
                # Floats for SVG geometry; tooltips format with "{:,.0f}".
                "gross": float(b["gross"]),
                "net": float(b["net"]),
            }
            for b in monthly_revenue
        ],
        "y_max": y_max,
        "ticks": ticks,
        "unit": "تومان",
    }


def _build_enrollments_chart(
    enrollment_trend: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """Chart model for monthly requests vs approvals (grouped bars).

    Counts use an integer axis (no fractional tick labels for people).
    """
    if not enrollment_trend:
        return None
    peak = max(
        [b["requested"] for b in enrollment_trend]
        + [b["approved"] for b in enrollment_trend]
    )
    step = max(1, int(_nice_ceiling(float(peak)) / 4))
    y_max = float(step * 4)
    return {
        "points": enrollment_trend,
        "y_max": y_max,
        "ticks": [float(step * f) for f in range(5)],
        "unit": "ثبت‌نام",
    }


def _build_attendance_chart(
    attendance_week: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """Chart model for 7-day attendance completion (0–100 scale)."""
    if not attendance_week:
        return None
    return {
        "points": attendance_week,
        "y_max": 100.0,
        "ticks": [0.0, 25.0, 50.0, 75.0, 100.0],
        "unit": "درصد",
    }


def _get_today_overview(today: date_type) -> dict[str, Any]:
    """Summarize today's sessions and their attendance-recording status.

    A session counts as recorded only when attendance rows exist for every
    approved enrollment — absence of records is never treated as presence.
    Sessions with no approved enrollments are neutral: never flagged as
    needing attention and excluded from the completion denominator.

    Runs three bounded queries regardless of session count (sessions with
    eager teacher profiles, eligible counts grouped by class, recorded
    counts grouped by session).
    """
    sessions = (
        SessionModel.query.options(
            joinedload(SessionModel.academy_class).joinedload(
                AcademyClassModel.teacher
            ),
        )
        .filter(
            SessionModel.scheduled_date == today,
            SessionModel.status != "CANCELLED",
        )
        .order_by(SessionModel.start_time)
        .limit(20)
        .all()
    )
    if not sessions:
        return {
            "date": today,
            "sessions": [],
            "total": 0,
            "recordable": 0,
            "recorded": 0,
            "completion_rate": None,
        }

    # Eager-load teacher profiles in one query (avoids per-row lazy loads).
    teacher_ids = {
        s.academy_class.teacher_user_id
        for s in sessions
        if s.academy_class is not None and s.academy_class.teacher_user_id
    }
    profiles = {}
    if teacher_ids:
        from app.infrastructure.database.models import TeacherProfileModel

        profiles = {
            p.user_id: p
            for p in TeacherProfileModel.query.filter(
                TeacherProfileModel.user_id.in_(teacher_ids)
            ).all()
        }

    class_ids = list({s.class_id for s in sessions})
    eligible_rows = (
        db.session.query(EnrollmentModel.class_id, func.count(EnrollmentModel.id))
        .filter(
            EnrollmentModel.class_id.in_(class_ids),
            EnrollmentModel.status == "APPROVED",
        )
        .group_by(EnrollmentModel.class_id)
        .all()
    )
    eligible_map = {class_id: count for class_id, count in eligible_rows}

    recorded_rows = (
        db.session.query(
            AttendanceModel.session_id,
            func.count(func.distinct(AttendanceModel.enrollment_id)),
        )
        .join(
            EnrollmentModel,
            AttendanceModel.enrollment_id == EnrollmentModel.id,
        )
        .filter(
            AttendanceModel.session_id.in_([s.id for s in sessions]),
            EnrollmentModel.status == "APPROVED",
        )
        .group_by(AttendanceModel.session_id)
        .all()
    )
    recorded_map = {session_id: count for session_id, count in recorded_rows}

    items: list[dict[str, Any]] = []
    recorded_count = 0
    for session in sessions:
        eligible = eligible_map.get(session.class_id, 0)
        recorded = recorded_map.get(session.id, 0)
        is_recorded = eligible > 0 and recorded >= eligible
        # Sessions with no approved enrollments cannot have attendance
        # recorded; they are neutral (never flagged as needing attention and
        # never counted in the completion denominator).
        needs_attention = eligible > 0 and not is_recorded
        if is_recorded:
            recorded_count += 1
        teacher_name = "—"
        academy_class = session.academy_class
        if academy_class is not None and academy_class.teacher_user_id:
            profile = profiles.get(academy_class.teacher_user_id)
            if profile is not None:
                teacher_name = f"{profile.first_name} {profile.last_name}"
            elif academy_class.teacher is not None:
                teacher_name = academy_class.teacher.login
        capacity = academy_class.capacity if academy_class is not None else 0
        fill_percent = round(eligible / capacity * 100) if capacity else 0
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
                "needs_attention": needs_attention,
                "capacity": capacity,
                "approved_count": eligible,
                "fill_percent": fill_percent,
            }
        )
    recordable = sum(1 for i in items if i["eligible_count"] > 0)
    return {
        "date": today,
        "sessions": items,
        "total": len(items),
        "recordable": recordable,
        "recorded": recorded_count,
        # None when there is no denominator — the template shows an
        # explicit "no classes today" state instead of 0%.
        "completion_rate": (recorded_count / recordable) if recordable else None,
    }


def _get_attendance_week(today: date_type) -> list[dict[str, Any]]:
    """Per-day attendance completion for the last ATTENDANCE_WEEK_DAYS days.

    Denominator per day: non-cancelled sessions dated that day that have at
    least one approved enrollment (neutral sessions excluded). Days without
    recordable sessions carry rate None (rendered as a gap, never as 0%).
    Three bounded queries regardless of session volume.
    """
    start_day = today - timedelta(days=ATTENDANCE_WEEK_DAYS - 1)
    sessions = (
        SessionModel.query.filter(
            SessionModel.scheduled_date >= start_day,
            SessionModel.scheduled_date <= today,
            SessionModel.status != "CANCELLED",
        )
        .order_by(SessionModel.scheduled_date, SessionModel.start_time)
        .limit(100)
        .all()
    )
    days: list[dict[str, Any]] = []
    for offset in range(ATTENDANCE_WEEK_DAYS):
        day = start_day + timedelta(days=offset)
        days.append(
            {
                "key": day.isoformat(),
                "label": WEEKDAY_NAMES_FA[day.weekday()],
                "recordable": 0,
                "recorded": 0,
                "rate": None,
            }
        )
    if not sessions:
        return days
    by_day: dict[str, list] = {}
    for session in sessions:
        by_day.setdefault(session.scheduled_date.isoformat(), []).append(session)

    class_ids = list({s.class_id for s in sessions})
    eligible_rows = (
        db.session.query(EnrollmentModel.class_id, func.count(EnrollmentModel.id))
        .filter(
            EnrollmentModel.class_id.in_(class_ids),
            EnrollmentModel.status == "APPROVED",
        )
        .group_by(EnrollmentModel.class_id)
        .all()
    )
    eligible_map = {class_id: count for class_id, count in eligible_rows}
    recorded_rows = (
        db.session.query(
            AttendanceModel.session_id,
            func.count(func.distinct(AttendanceModel.enrollment_id)),
        )
        .join(
            EnrollmentModel,
            AttendanceModel.enrollment_id == EnrollmentModel.id,
        )
        .filter(
            AttendanceModel.session_id.in_([s.id for s in sessions]),
            EnrollmentModel.status == "APPROVED",
        )
        .group_by(AttendanceModel.session_id)
        .all()
    )
    recorded_map = {session_id: count for session_id, count in recorded_rows}

    for day in days:
        for session in by_day.get(day["key"], []):
            eligible = eligible_map.get(session.class_id, 0)
            if eligible == 0:
                continue
            day["recordable"] += 1
            if recorded_map.get(session.id, 0) >= eligible:
                day["recorded"] += 1
        if day["recordable"]:
            day["rate"] = day["recorded"] / day["recordable"]
    return days


def _get_capacity_watch(limit: int = 5) -> list[dict[str, Any]]:
    """Operational classes at or above FULL_CAPACITY_THRESHOLD fill ratio.

    Single grouped query; approvals can never exceed capacity (enforced at
    approval time), so these classes need planning attention before closing.
    """
    rows = (
        db.session.query(
            AcademyClassModel.id,
            AcademyClassModel.title,
            AcademyClassModel.capacity,
            AcademyClassModel.status,
            func.count(EnrollmentModel.id),
        )
        .outerjoin(
            EnrollmentModel,
            db.and_(
                EnrollmentModel.class_id == AcademyClassModel.id,
                EnrollmentModel.status == "APPROVED",
            ),
        )
        .filter(
            AcademyClassModel.status.in_(OPERATIONAL_CLASS_STATUSES),
            AcademyClassModel.capacity > 0,
        )
        .group_by(
            AcademyClassModel.id,
            AcademyClassModel.title,
            AcademyClassModel.capacity,
            AcademyClassModel.status,
        )
        .all()
    )
    watch = []
    for class_id, title, capacity, status, approved in rows:
        ratio = (approved or 0) / capacity
        if ratio >= FULL_CAPACITY_THRESHOLD:
            watch.append(
                {
                    "class_id": class_id,
                    "title": title,
                    "status": status,
                    "capacity": capacity,
                    "approved": approved or 0,
                    "fill_percent": round(ratio * 100),
                }
            )
    watch.sort(key=lambda w: w["fill_percent"], reverse=True)
    return watch[:limit]


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
    open_assessments: int,
    closed_assessments: int,
    today_overview: dict[str, Any] | None,
    capacity_watch: list[dict[str, Any]] | None,
    running_classes: int,
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
        unrecorded = sum(1 for s in today_overview["sessions"] if s["needs_attention"])
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
    if open_assessments > 0:
        items.append(
            {
                "severity": "info",
                "message": (f"{open_assessments} آزمون باز در حال برگزاری است."),
                "count": open_assessments,
                "endpoint": "assessment.admin_assessment_list",
                "endpoint_args": {"status": "OPEN"},
                "action_label": "مشاهده آزمون‌های باز",
            }
        )
    if closed_assessments > 0:
        items.append(
            {
                "severity": "warning",
                "message": (
                    f"{closed_assessments} آزمون بسته‌شده در انتظار نمره‌گذاری است."
                ),
                "count": closed_assessments,
                "endpoint": "assessment.admin_assessment_list",
                "endpoint_args": {"status": "CLOSED"},
                "action_label": "مشاهده آزمون‌های بسته‌شده",
            }
        )
    if capacity_watch:
        full = capacity_watch[0]
        items.append(
            {
                "severity": "info",
                "message": (
                    f"کلاس «{full['title']}» با {full['fill_percent']}٪ ظرفیت "
                    f"({full['approved']} از {full['capacity']} نفر) نزدیک به تکمیل است."
                ),
                "count": len(capacity_watch),
                "endpoint": "academy.class_detail",
                "endpoint_args": {"class_id": full["class_id"]},
                "action_label": "مشاهده کلاس",
            }
        )
    if active_students == 0 and running_classes == 0:
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
