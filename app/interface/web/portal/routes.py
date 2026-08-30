"""Portal routes — role-specific dashboards."""

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
