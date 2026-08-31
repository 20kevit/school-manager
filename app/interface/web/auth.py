from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.application.auth.services import (
    AuthenticationError,
    change_password,
    login_authenticated_user,
    logout_current_user,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page and handler."""
    if request.method == "POST":
        login_id = request.form.get("login", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        if not login_id or not password:
            flash("Please enter login and password.", "error")
            return render_template("auth/login.html"), 400

        try:
            from app.application.auth.services import authenticate

            user = authenticate(login_id, password)
            login_authenticated_user(user, remember=remember)
            flash("Login successful.", "success")
            return redirect(url_for("auth.dashboard"))
        except AuthenticationError:
            flash("Invalid login or password.", "error")
            return render_template("auth/login.html"), 401

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Log out the current user."""
    logout_current_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    """Dashboard page for authenticated users — redirects to role-specific portal."""
    if current_user.has_any_role("ADMIN"):
        return redirect(url_for("portal.admin_dashboard"))
    if current_user.has_any_role("TEACHER"):
        return redirect(url_for("portal.teacher_dashboard"))
    if current_user.has_any_role("STUDENT"):
        return redirect(url_for("portal.student_dashboard"))
    if current_user.has_any_role("PARENT"):
        return redirect(url_for("portal.parent_dashboard"))
    return render_template("auth/dashboard.html")


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password_view():
    """Change password page and handler."""
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not current_password or not new_password:
            flash("Please fill in all fields.", "error")
            return render_template("auth/change_password.html"), 400

        if new_password != confirm_password:
            flash("New passwords do not match.", "error")
            return render_template("auth/change_password.html"), 400

        if len(new_password) < 6:
            flash("New password must be at least 6 characters.", "error")
            return render_template("auth/change_password.html"), 400

        try:
            change_password(current_user, current_password, new_password)
            flash("Password changed successfully.", "success")
            return redirect(url_for("auth.dashboard"))
        except AuthenticationError:
            flash("Current password is incorrect.", "error")
            return render_template("auth/change_password.html"), 400

    return render_template("auth/change_password.html")


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """View and edit user profile."""
    from app.extensions import db
    from app.infrastructure.database.models import (
        ParentProfileModel,
        StudentProfileModel,
        TeacherProfileModel,
    )

    profile_obj = None
    profile_type = None

    if current_user.has_any_role("STUDENT"):
        profile_obj = StudentProfileModel.query.filter_by(
            user_id=current_user.id
        ).first()
        profile_type = "student"
    elif current_user.has_any_role("TEACHER"):
        profile_obj = TeacherProfileModel.query.filter_by(
            user_id=current_user.id
        ).first()
        profile_type = "teacher"
    elif current_user.has_any_role("PARENT"):
        profile_obj = ParentProfileModel.query.filter_by(
            user_id=current_user.id
        ).first()
        profile_type = "parent"

    if request.method == "POST" and profile_obj:
        try:
            first_name = request.form.get("first_name", "").strip()
            last_name = request.form.get("last_name", "").strip()
            mobile_phone = request.form.get("mobile_phone", "").strip()

            if not first_name or not last_name:
                flash("نام و نام خانوادگی الزامی است.", "error")
                return render_template(
                    "auth/profile.html", profile=profile_obj, profile_type=profile_type
                )

            profile_obj.first_name = first_name
            profile_obj.last_name = last_name
            if mobile_phone:
                profile_obj.mobile_phone = mobile_phone

            if profile_type == "student":
                birth_date_str = request.form.get("birth_date", "")
                gender = request.form.get("gender", "")
                if birth_date_str:
                    from datetime import date as date_type

                    parts = birth_date_str.split("-")
                    if len(parts) == 3:
                        profile_obj.birth_date = date_type(
                            int(parts[0]), int(parts[1]), int(parts[2])
                        )
                if gender:
                    profile_obj.gender = gender

            db.session.commit()
            flash("پروفایل با موفقیت به‌روزرسانی شد.", "success")
            return redirect(url_for("auth.profile"))
        except Exception:
            db.session.rollback()
            flash("خطا در به‌روزرسانی پروفایل.", "error")

    return render_template(
        "auth/profile.html", profile=profile_obj, profile_type=profile_type
    )
