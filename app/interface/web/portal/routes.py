"""Portal routes — role-specific dashboards."""

from datetime import date, datetime, timedelta

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.interface.web.decorators import role_required

portal_bp = Blueprint("portal", __name__, url_prefix="/portal")


# ---------------------------------------------------------------------------
# Student Dashboard
# ---------------------------------------------------------------------------


@portal_bp.route("/student")
@login_required
@role_required("STUDENT")
def student_dashboard():
    """Student dashboard with academic, attendance, and financial overview."""
    from app.application.portal.portal_service import get_student_dashboard

    data = get_student_dashboard(current_user.id)
    return render_template("portal/student.html", data=data)


# ---------------------------------------------------------------------------
# Parent Dashboard
# ---------------------------------------------------------------------------


@portal_bp.route("/parent")
@login_required
@role_required("PARENT")
def parent_dashboard():
    """Parent dashboard with children overview."""
    from app.application.portal.portal_service import get_parent_dashboard

    data = get_parent_dashboard(current_user.id)
    return render_template("portal/parent.html", data=data)


# ---------------------------------------------------------------------------
# Teacher Dashboard
# ---------------------------------------------------------------------------


@portal_bp.route("/teacher")
@login_required
@role_required("TEACHER")
def teacher_dashboard():
    """Teacher dashboard with classes, students, and grading overview."""
    from app.application.portal.portal_service import get_teacher_dashboard

    data = get_teacher_dashboard(current_user.id)
    return render_template("portal/teacher.html", data=data)


# ---------------------------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------------------------


@portal_bp.route("/admin")
@login_required
@role_required("ADMIN")
def admin_dashboard():
    """Admin dashboard with system-wide overview."""
    from app.application.portal.portal_service import get_admin_dashboard

    data = get_admin_dashboard()
    return render_template("portal/admin.html", data=data)


# ---------------------------------------------------------------------------
# Timetable
# ---------------------------------------------------------------------------

WEEKDAYS = [
    "SATURDAY",
    "SUNDAY",
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
]


def _build_timetable_data(schedule_entries):
    """Build a weekly timetable grid from schedule entries.

    Returns a dict keyed by weekday, each containing a list of
    {"class_title", "course_title", "start_time", "end_time", "class_id", "online_link"}.
    """
    grid: dict[str, list[dict]] = {d: [] for d in WEEKDAYS}
    for entry in schedule_entries:
        cls = entry.academy_class
        course = cls.course if cls.course else None
        grid[entry.weekday].append(
            {
                "class_id": cls.id,
                "class_title": cls.title,
                "course_title": course.title if course else "",
                "start_time": entry.start_time,
                "end_time": entry.end_time,
                "online_link": cls.online_link,
            }
        )
    for day in grid:
        grid[day].sort(key=lambda x: x["start_time"])
    return grid


def _get_upcoming_sessions(class_ids: list[int]) -> list[dict]:
    """Get upcoming sessions (today, within 30 minutes) with online links for given classes."""
    from app.infrastructure.database.models import SessionModel

    if not class_ids:
        return []

    today = date.today()
    now = datetime.now()
    cutoff = now + timedelta(minutes=30)

    sessions = SessionModel.query.filter(
        SessionModel.class_id.in_(class_ids),
        SessionModel.scheduled_date == today,
        SessionModel.status == "SCHEDULED",
    ).all()

    upcoming = []
    for s in sessions:
        session_start = datetime.combine(s.scheduled_date, s.start_time)
        session_end = datetime.combine(s.scheduled_date, s.end_time)
        if session_start <= cutoff and session_end >= now:
            effective_link = s.online_link or (
                s.academy_class.online_link if s.academy_class else None
            )
            if effective_link:
                upcoming.append(
                    {
                        "session": s,
                        "online_link": effective_link,
                        "class_title": s.academy_class.title if s.academy_class else "",
                    }
                )
    return upcoming


@portal_bp.route("/student/timetable")
@login_required
@role_required("STUDENT")
def student_timetable():
    """Student weekly timetable view."""
    from app.infrastructure.database.models import (
        ClassScheduleModel,
        EnrollmentModel,
    )

    enrollments = EnrollmentModel.query.filter_by(
        student_user_id=current_user.id, status="APPROVED"
    ).all()
    class_ids = [e.class_id for e in enrollments]

    schedule_entries = []
    if class_ids:
        schedule_entries = ClassScheduleModel.query.filter(
            ClassScheduleModel.class_id.in_(class_ids)
        ).all()

    timetable = _build_timetable_data(schedule_entries)
    upcoming = _get_upcoming_sessions(class_ids)
    return render_template(
        "portal/timetable.html",
        timetable=timetable,
        role="student",
        upcoming_sessions=upcoming,
    )


@portal_bp.route("/teacher/timetable")
@login_required
@role_required("TEACHER")
def teacher_timetable():
    """Teacher weekly timetable view."""
    from app.infrastructure.database.models import (
        AcademyClassModel,
        ClassScheduleModel,
    )

    classes = (
        AcademyClassModel.query.filter_by(teacher_user_id=current_user.id)
        .filter(AcademyClassModel.status.in_(["PLANNED", "ACTIVE"]))
        .all()
    )
    class_ids = [c.id for c in classes]

    schedule_entries = []
    if class_ids:
        schedule_entries = ClassScheduleModel.query.filter(
            ClassScheduleModel.class_id.in_(class_ids)
        ).all()

    timetable = _build_timetable_data(schedule_entries)
    upcoming = _get_upcoming_sessions(class_ids)
    return render_template(
        "portal/timetable.html",
        timetable=timetable,
        role="teacher",
        upcoming_sessions=upcoming,
    )
