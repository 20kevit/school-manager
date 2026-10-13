from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.application.attendance.attendance_service import (
    AttendanceError,
    compute_session_summary,
    compute_student_summary,
    get_eligible_enrollments,
    get_session_attendance,
    get_student_attendance,
    is_teacher_of_class,
    record_session_attendance,
)
from app.infrastructure.database.models import (
    AcademyClassModel,
    SessionModel,
    UserModel,
)
from app.interface.web.decorators import role_required
from app.utils.flash import flash_safe_error

attendance_bp = Blueprint("attendance", __name__, url_prefix="/attendance")


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------


@attendance_bp.route("/admin/all")
@login_required
@role_required("ADMIN")
def admin_attendance_list():
    """List all sessions with attendance overview."""
    class_id = request.args.get("class_id", type=int)

    if class_id:
        sessions = (
            SessionModel.query.filter_by(class_id=class_id)
            .order_by(SessionModel.scheduled_date.desc())
            .all()
        )
    else:
        sessions = (
            SessionModel.query.order_by(SessionModel.scheduled_date.desc())
            .limit(50)
            .all()
        )

    classes = AcademyClassModel.query.order_by(AcademyClassModel.title).all()

    session_summaries = {}
    for s in sessions:
        session_summaries[s.id] = compute_session_summary(s.id)

    return render_template(
        "attendance/admin_list.html",
        sessions=sessions,
        classes=classes,
        selected_class_id=class_id,
        session_summaries=session_summaries,
    )


@attendance_bp.route("/admin/session/<int:session_id>")
@login_required
@role_required("ADMIN")
def admin_session_attendance(session_id):
    """View and take attendance for a session (admin)."""
    session = SessionModel.query.get(session_id)
    if session is None:
        flash("Session not found.", "error")
        return redirect(url_for("attendance.admin_attendance_list"))

    academy_class = AcademyClassModel.query.get(session.class_id)
    eligible = get_eligible_enrollments(session_id)
    existing = get_session_attendance(session_id)

    existing_map = {a.enrollment_id: a for a in existing}
    summary = compute_session_summary(session_id)

    return render_template(
        "attendance/session_attendance.html",
        session=session,
        academy_class=academy_class,
        eligible=enrollments_with_students(eligible),
        existing_map=existing_map,
        summary=summary,
        is_admin=True,
    )


@attendance_bp.route("/admin/session/<int:session_id>/save", methods=["POST"])
@login_required
@role_required("ADMIN")
def admin_save_session_attendance(session_id):
    """Save attendance for a session (admin)."""
    session = SessionModel.query.get(session_id)
    if session is None:
        flash("Session not found.", "error")
        return redirect(url_for("attendance.admin_attendance_list"))

    attendance_data = _parse_attendance_form(request.form)

    try:
        record_session_attendance(
            session_id=session_id,
            attendance_data=attendance_data,
            recorded_by=current_user.id,
        )
        flash("Attendance saved successfully.", "success")
    except AttendanceError as e:
        flash_safe_error(e)

    return redirect(
        url_for("attendance.admin_session_attendance", session_id=session_id)
    )


# ---------------------------------------------------------------------------
# Teacher routes
# ---------------------------------------------------------------------------


@attendance_bp.route("/teacher/my-classes")
@login_required
@role_required("TEACHER")
def teacher_my_classes():
    """List teacher's assigned classes."""
    classes = (
        AcademyClassModel.query.filter_by(teacher_user_id=current_user.id)
        .order_by(AcademyClassModel.title)
        .all()
    )
    return render_template("attendance/teacher_classes.html", classes=classes)


@attendance_bp.route("/teacher/class/<int:class_id>/sessions")
@login_required
@role_required("TEACHER")
def teacher_class_sessions(class_id):
    """List sessions for a teacher's class."""
    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        flash("Class not found.", "error")
        return redirect(url_for("attendance.teacher_my_classes"))

    if not is_teacher_of_class(current_user.id, class_id):
        abort(403)

    sessions = (
        SessionModel.query.filter_by(class_id=class_id)
        .order_by(SessionModel.session_number)
        .all()
    )

    session_summaries = {}
    for s in sessions:
        session_summaries[s.id] = compute_session_summary(s.id)

    return render_template(
        "attendance/teacher_sessions.html",
        academy_class=academy_class,
        sessions=sessions,
        session_summaries=session_summaries,
    )


@attendance_bp.route("/teacher/session/<int:session_id>")
@login_required
@role_required("TEACHER")
def teacher_session_attendance(session_id):
    """View and take attendance for a session (teacher)."""
    session = SessionModel.query.get(session_id)
    if session is None:
        flash("Session not found.", "error")
        return redirect(url_for("attendance.teacher_my_classes"))

    if not is_teacher_of_class(current_user.id, session.class_id):
        abort(403)

    academy_class = AcademyClassModel.query.get(session.class_id)
    eligible = get_eligible_enrollments(session_id)
    existing = get_session_attendance(session_id)

    existing_map = {a.enrollment_id: a for a in existing}
    summary = compute_session_summary(session_id)

    return render_template(
        "attendance/session_attendance.html",
        session=session,
        academy_class=academy_class,
        eligible=enrollments_with_students(eligible),
        existing_map=existing_map,
        summary=summary,
        is_admin=False,
    )


@attendance_bp.route("/teacher/session/<int:session_id>/save", methods=["POST"])
@login_required
@role_required("TEACHER")
def teacher_save_session_attendance(session_id):
    """Save attendance for a session (teacher)."""
    session = SessionModel.query.get(session_id)
    if session is None:
        flash("Session not found.", "error")
        return redirect(url_for("attendance.teacher_my_classes"))

    if not is_teacher_of_class(current_user.id, session.class_id):
        abort(403)

    attendance_data = _parse_attendance_form(request.form)

    try:
        record_session_attendance(
            session_id=session_id,
            attendance_data=attendance_data,
            recorded_by=current_user.id,
        )
        flash("Attendance saved successfully.", "success")
    except AttendanceError as e:
        flash_safe_error(e)

    return redirect(
        url_for("attendance.teacher_session_attendance", session_id=session_id)
    )


# ---------------------------------------------------------------------------
# Student routes
# ---------------------------------------------------------------------------


@attendance_bp.route("/student/my-attendance")
@login_required
@role_required("STUDENT")
def student_my_attendance():
    """View student's own attendance history."""
    records = get_student_attendance(current_user.id)
    summary = compute_student_summary(current_user.id)
    return render_template(
        "attendance/student_attendance.html",
        records=records,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def enrollments_with_students(enrollments):
    """Attach student user objects to enrollments for template rendering."""
    result = []
    for e in enrollments:
        student = UserModel.query.get(e.student_user_id)
        result.append({"enrollment": e, "student": student})
    return result


def _parse_attendance_form(form) -> list[dict]:
    """Parse the bulk attendance form data.

    Form fields are named: attendance_<enrollment_id>_status, attendance_<enrollment_id>_note
    """
    data = []
    processed = set()

    for key in form:
        if key.startswith("attendance_") and key.endswith("_status"):
            enrollment_id_str = key[len("attendance_") : -len("_status")]
            try:
                enrollment_id = int(enrollment_id_str)
            except ValueError:
                continue

            if enrollment_id in processed:
                continue
            processed.add(enrollment_id)

            status = form.get(key, "")
            note = form.get(f"attendance_{enrollment_id}_note", "")

            if status:
                data.append(
                    {
                        "enrollment_id": enrollment_id,
                        "status": status,
                        "note": note,
                    }
                )

    return data
