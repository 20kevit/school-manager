"""Admin user management routes."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.application.auth.services import (
    assign_role,
    create_user,
    get_user_profile_data,
    link_parent_student,
    list_users,
    unlink_parent_student,
    update_user_profile,
)
from app.extensions import db
from app.infrastructure.database.models import StudentProfileModel
from app.interface.web.decorators import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ---------------------------------------------------------------------------
# User List
# ---------------------------------------------------------------------------


@admin_bp.route("/users")
@login_required
@role_required("ADMIN")
def user_list():
    """List all users with search and role filters."""
    search = request.args.get("search", "").strip()
    role_filter = request.args.get("role", "").strip()
    page = request.args.get("page", 1, type=int)

    users, total = list_users(
        search=search, role_filter=role_filter, page=page, per_page=20
    )
    total_pages = (total + 19) // 20

    return render_template(
        "admin/user_list.html",
        users=users,
        total=total,
        page=page,
        total_pages=total_pages,
        search=search,
        role_filter=role_filter,
    )


# ---------------------------------------------------------------------------
# Create User
# ---------------------------------------------------------------------------


@admin_bp.route("/users/create", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def user_create():
    """Create a new user with role-specific profile."""
    if request.method == "POST":
        login = request.form.get("login", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "").strip()

        if not login or not password or not role:
            flash("نام کاربری، رمز عبور و نقش الزامی هستند.", "error")
            return render_template("admin/user_form.html")

        if role not in ("ADMIN", "TEACHER", "STUDENT", "PARENT"):
            flash("نقش نامعتبر است.", "error")
            return render_template("admin/user_form.html")

        try:
            if role == "ADMIN":
                user = create_user(login, password)
                assign_role(user, "ADMIN")
            elif role == "TEACHER":
                national_id = request.form.get("national_id", "").strip()
                first_name = request.form.get("first_name", "").strip()
                last_name = request.form.get("last_name", "").strip()
                mobile_phone = request.form.get("mobile_phone", "").strip()

                if not all([national_id, first_name, last_name, mobile_phone]):
                    flash("تمام فیلدهای پروفایل معلم الزامی هستند.", "error")
                    return render_template("admin/user_form.html", role=role)

                from app.application.auth.services import create_teacher_user

                create_teacher_user(
                    login=login,
                    password=password,
                    national_id=national_id,
                    first_name=first_name,
                    last_name=last_name,
                    mobile_phone=mobile_phone,
                )
            elif role == "STUDENT":
                national_id = request.form.get("national_id", "").strip()
                first_name = request.form.get("first_name", "").strip()
                last_name = request.form.get("last_name", "").strip()
                mobile_phone = request.form.get("mobile_phone", "").strip()
                birth_date_str = request.form.get("birth_date", "").strip()
                gender = request.form.get("gender", "").strip()

                if not all(
                    [
                        national_id,
                        first_name,
                        last_name,
                        mobile_phone,
                        birth_date_str,
                        gender,
                    ]
                ):
                    flash("تمام فیلدهای پروفایل دانش‌آموز الزامی هستند.", "error")
                    return render_template("admin/user_form.html", role=role)

                from app.utils.date_utils import parse_jalali_date

                try:
                    birth_date = parse_jalali_date(birth_date_str)
                except ValueError as e:
                    flash(str(e), "error")
                    return render_template("admin/user_form.html", role=role)

                from app.application.auth.services import create_student_user

                create_student_user(
                    login=login,
                    national_id=national_id,
                    first_name=first_name,
                    last_name=last_name,
                    mobile_phone=mobile_phone,
                    birth_date=birth_date,
                    gender=gender,
                )
            elif role == "PARENT":
                national_id = request.form.get("national_id", "").strip()
                first_name = request.form.get("first_name", "").strip()
                last_name = request.form.get("last_name", "").strip()
                mobile_phone = request.form.get("mobile_phone", "").strip()

                if not all([national_id, first_name, last_name, mobile_phone]):
                    flash("تمام فیلدهای پروفایل والدین الزامی هستند.", "error")
                    return render_template("admin/user_form.html", role=role)

                from app.application.auth.services import create_parent_user

                create_parent_user(
                    login=login,
                    password=password,
                    national_id=national_id,
                    first_name=first_name,
                    last_name=last_name,
                    mobile_phone=mobile_phone,
                )

            flash("کاربر با موفقیت ایجاد شد.", "success")
            return redirect(url_for("admin.user_list"))

        except Exception as e:
            db.session.rollback()
            flash(f"خطا در ایجاد کاربر: {e}", "error")

    return render_template("admin/user_form.html")


# ---------------------------------------------------------------------------
# Edit User
# ---------------------------------------------------------------------------


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def user_edit(user_id):
    """Edit user profile and manage parent-student links."""
    try:
        data = get_user_profile_data(user_id)
    except ValueError:
        flash("کاربر یافت نشد.", "error")
        return redirect(url_for("admin.user_list"))

    user = data["user"]
    profile = data["profile"]
    profile_type = data["profile_type"]

    if request.method == "POST":
        action = request.form.get("action", "update_profile")

        if action == "update_profile":
            try:
                kwargs = {}
                if profile_type in ("student", "teacher", "parent"):
                    kwargs["first_name"] = request.form.get("first_name", "").strip()
                    kwargs["last_name"] = request.form.get("last_name", "").strip()
                    kwargs["mobile_phone"] = request.form.get(
                        "mobile_phone", ""
                    ).strip()
                    kwargs["national_id"] = request.form.get("national_id", "").strip()

                if profile_type == "student":
                    kwargs["gender"] = request.form.get("gender", "").strip()
                    birth_date_str = request.form.get("birth_date", "").strip()
                    if birth_date_str:
                        from app.utils.date_utils import parse_jalali_date

                        try:
                            kwargs["birth_date"] = parse_jalali_date(birth_date_str)
                        except ValueError as e:
                            flash(str(e), "error")
                            return render_template(
                                "admin/user_edit.html",
                                user=user,
                                profile=profile,
                                profile_type=profile_type,
                            )

                update_user_profile(user, **kwargs)
                flash("پروفایل با موفقیت به‌روزرسانی شد.", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"خطا در به‌روزرسانی پروفایل: {e}", "error")

        elif action == "reset_password":
            new_password = request.form.get("new_password", "").strip()
            if not new_password or len(new_password) < 6:
                flash("رمز عبور جدید باید حداقل ۶ کاراکتر باشد.", "error")
            else:
                user.set_password(new_password)
                db.session.commit()
                flash("رمز عبور با موفقیت تغییر کرد.", "success")

        elif action == "toggle_active":
            user.is_active_user = not user.is_active_user
            db.session.commit()
            status = "فعال" if user.is_active_user else "غیرفعال"
            flash(f"کاربر {status} شد.", "success")

        elif action == "link_student":
            student_user_id = request.form.get("student_user_id", type=int)
            if student_user_id:
                try:
                    link_parent_student(user.id, student_user_id)
                    flash("دانش‌آموز با موفقیت لینک شد.", "success")
                except ValueError as e:
                    flash(str(e), "error")

        elif action == "unlink_student":
            student_user_id = request.form.get("student_user_id", type=int)
            if student_user_id:
                try:
                    unlink_parent_student(user.id, student_user_id)
                    flash("لینک دانش‌آموز حذف شد.", "success")
                except ValueError as e:
                    flash(str(e), "error")

        return redirect(url_for("admin.user_edit", user_id=user.id))

    # For parent users, fetch linked and available students
    linked_students = []
    available_students = []
    if profile_type == "parent" and profile:
        linked_students = profile.children
        linked_ids = {s.user_id for s in linked_students}
        available_students = StudentProfileModel.query.filter(
            ~StudentProfileModel.user_id.in_(linked_ids)
        ).all()

    return render_template(
        "admin/user_edit.html",
        user=user,
        profile=profile,
        profile_type=profile_type,
        linked_students=linked_students,
        available_students=available_students,
    )
