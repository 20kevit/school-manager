"""Admin user management routes."""

from datetime import date
from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.application.academic_calendar.service import (
    AcademicCalendarError,
    create_academic_year,
    create_calendar_event,
    create_semester,
    delete_academic_year,
    delete_calendar_event,
    delete_semester,
    get_academic_year,
    get_calendar_event,
    get_semester,
    list_academic_years,
    list_calendar_events,
    list_semesters,
    update_academic_year,
    update_calendar_event,
    update_semester,
)
from app.application.academy.class_service import (
    get_class,
    regenerate_sessions,
)
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
from app.utils.date_utils import parse_jalali_date

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


# ---------------------------------------------------------------------------
# Academic Year Management
# ---------------------------------------------------------------------------


@admin_bp.route("/years")
@login_required
@role_required("ADMIN")
def year_list():
    years = list_academic_years()
    return render_template("admin/year_list.html", years=years)


@admin_bp.route("/years/create", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def year_create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        start_date_str = request.form.get("start_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip()
        is_active = request.form.get("is_active") == "on"

        if not title or not start_date_str or not end_date_str:
            flash("تمام فیلدها الزامی هستند.", "error")
            return render_template("admin/year_form.html")

        try:
            start_date = parse_jalali_date(start_date_str)
            end_date = parse_jalali_date(end_date_str)
        except ValueError as e:
            flash(str(e), "error")
            return render_template("admin/year_form.html")

        try:
            create_academic_year(title, start_date, end_date, is_active)
            flash("سال تحصیلی با موفقیت ایجاد شد.", "success")
            return redirect(url_for("admin.year_list"))
        except AcademicCalendarError as e:
            flash(str(e), "error")

    return render_template("admin/year_form.html")


@admin_bp.route("/years/<int:year_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def year_edit(year_id):
    year = get_academic_year(year_id)
    if year is None:
        flash("سال تحصیلی یافت نشد.", "error")
        return redirect(url_for("admin.year_list"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        start_date_str = request.form.get("start_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip()
        is_active = request.form.get("is_active") == "on"

        try:
            start_date = (
                parse_jalali_date(start_date_str) if start_date_str else year.start_date
            )
            end_date = (
                parse_jalali_date(end_date_str) if end_date_str else year.end_date
            )
            update_academic_year(
                year,
                title=title or None,
                start_date=start_date,
                end_date=end_date,
                is_active=is_active,
            )
            flash("سال تحصیلی با موفقیت به‌روزرسانی شد.", "success")
            return redirect(url_for("admin.year_list"))
        except AcademicCalendarError as e:
            flash(str(e), "error")

    return render_template("admin/year_form.html", year=year)


@admin_bp.route("/years/<int:year_id>/delete", methods=["POST"])
@login_required
@role_required("ADMIN")
def year_delete(year_id):
    year = get_academic_year(year_id)
    if year is None:
        flash("سال تحصیلی یافت نشد.", "error")
        return redirect(url_for("admin.year_list"))
    delete_academic_year(year)
    flash("سال تحصیلی حذف شد.", "success")
    return redirect(url_for("admin.year_list"))


# ---------------------------------------------------------------------------
# Semester Management
# ---------------------------------------------------------------------------


@admin_bp.route("/semesters")
@login_required
@role_required("ADMIN")
def semester_list():
    year_id = request.args.get("year_id", type=int)
    semesters = list_semesters(academic_year_id=year_id)
    years = list_academic_years()
    return render_template(
        "admin/semester_list.html",
        semesters=semesters,
        years=years,
        selected_year_id=year_id,
    )


@admin_bp.route("/semesters/create", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def semester_create():
    years = list_academic_years()
    preselect_year_id = request.args.get("year_id", type=int)

    if request.method == "POST":
        academic_year_id = request.form.get("academic_year_id", type=int)
        title = request.form.get("title", "").strip()
        start_date_str = request.form.get("start_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip()
        is_active = request.form.get("is_active") == "on"

        if not academic_year_id or not title or not start_date_str or not end_date_str:
            flash("تمام فیلدها الزامی هستند.", "error")
            return render_template("admin/semester_form.html", years=years)

        try:
            start_date = parse_jalali_date(start_date_str)
            end_date = parse_jalali_date(end_date_str)
        except ValueError as e:
            flash(str(e), "error")
            return render_template("admin/semester_form.html", years=years)

        try:
            create_semester(academic_year_id, title, start_date, end_date, is_active)
            flash("نیم‌سال با موفقیت ایجاد شد.", "success")
            return redirect(url_for("admin.semester_list"))
        except AcademicCalendarError as e:
            flash(str(e), "error")

    return render_template(
        "admin/semester_form.html", years=years, preselect_year_id=preselect_year_id
    )


@admin_bp.route("/semesters/<int:semester_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def semester_edit(semester_id):
    semester = get_semester(semester_id)
    if semester is None:
        flash("نیم‌سال یافت نشد.", "error")
        return redirect(url_for("admin.semester_list"))
    years = list_academic_years()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        start_date_str = request.form.get("start_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip()
        is_active = request.form.get("is_active") == "on"

        try:
            start_date = (
                parse_jalali_date(start_date_str)
                if start_date_str
                else semester.start_date
            )
            end_date = (
                parse_jalali_date(end_date_str) if end_date_str else semester.end_date
            )
            update_semester(
                semester,
                title=title or None,
                start_date=start_date,
                end_date=end_date,
                is_active=is_active,
            )
            flash("نیم‌سال با موفقیت به‌روزرسانی شد.", "success")
            return redirect(url_for("admin.semester_list"))
        except AcademicCalendarError as e:
            flash(str(e), "error")

    return render_template("admin/semester_form.html", semester=semester, years=years)


@admin_bp.route("/semesters/<int:semester_id>/delete", methods=["POST"])
@login_required
@role_required("ADMIN")
def semester_delete(semester_id):
    semester = get_semester(semester_id)
    if semester is None:
        flash("نیم‌سال یافت نشد.", "error")
        return redirect(url_for("admin.semester_list"))
    delete_semester(semester)
    flash("نیم‌سال حذف شد.", "success")
    return redirect(url_for("admin.semester_list"))


# ---------------------------------------------------------------------------
# Academic Calendar Events (Holidays)
# ---------------------------------------------------------------------------


@admin_bp.route("/calendar")
@login_required
@role_required("ADMIN")
def calendar_list():
    events = list_calendar_events()
    return render_template("admin/calendar_list.html", events=events)


@admin_bp.route("/calendar/create", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def calendar_create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        start_date_str = request.form.get("start_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip()
        is_recurring = request.form.get("is_recurring") == "on"
        description = request.form.get("description", "").strip()

        if not title or not start_date_str:
            flash("عنوان و تاریخ شروع الزامی هستند.", "error")
            return render_template("admin/calendar_form.html")

        try:
            start_date = parse_jalali_date(start_date_str)
            end_date = parse_jalali_date(end_date_str) if end_date_str else None
        except ValueError as e:
            flash(str(e), "error")
            return render_template("admin/calendar_form.html")

        try:
            create_calendar_event(
                title, start_date, end_date, is_recurring, description
            )
            flash("رویداد تقویم با موفقیت ایجاد شد.", "success")
            return redirect(url_for("admin.calendar_list"))
        except AcademicCalendarError as e:
            flash(str(e), "error")

    return render_template("admin/calendar_form.html")


@admin_bp.route("/calendar/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def calendar_edit(event_id):
    event = get_calendar_event(event_id)
    if event is None:
        flash("رویداد یافت نشد.", "error")
        return redirect(url_for("admin.calendar_list"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        start_date_str = request.form.get("start_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip()
        is_recurring = request.form.get("is_recurring") == "on"
        description = request.form.get("description", "").strip()

        try:
            start_date = (
                parse_jalali_date(start_date_str)
                if start_date_str
                else event.start_date
            )
            end_date = parse_jalali_date(end_date_str) if end_date_str else None
            update_calendar_event(
                event,
                title=title or None,
                start_date=start_date,
                end_date=end_date,
                is_recurring=is_recurring,
                description=description,
            )
            flash("رویداد تقویم با موفقیت به‌روزرسانی شد.", "success")
            return redirect(url_for("admin.calendar_list"))
        except AcademicCalendarError as e:
            flash(str(e), "error")

    return render_template("admin/calendar_form.html", event=event)


@admin_bp.route("/calendar/<int:event_id>/delete", methods=["POST"])
@login_required
@role_required("ADMIN")
def calendar_delete(event_id):
    event = get_calendar_event(event_id)
    if event is None:
        flash("رویداد یافت نشد.", "error")
        return redirect(url_for("admin.calendar_list"))
    delete_calendar_event(event)
    flash("رویداد تقویم حذف شد.", "success")
    return redirect(url_for("admin.calendar_list"))


# ---------------------------------------------------------------------------
# Session Regeneration
# ---------------------------------------------------------------------------


@admin_bp.route("/classes/<int:class_id>/regenerate-sessions", methods=["POST"])
@login_required
@role_required("ADMIN")
def class_regenerate_sessions(class_id):
    academy_class = get_class(class_id)
    if academy_class is None:
        flash("کلاس یافت نشد.", "error")
        return redirect(url_for("academy.class_list"))

    try:
        sessions = regenerate_sessions(academy_class)
        flash(
            f"جلسات با موفقیت بازسازی شدند. تعداد جلسات: {len(sessions)}.",
            "success",
        )
    except Exception as e:
        db.session.rollback()
        flash(f"خطا در بازسازی جلسات: {e}", "error")

    return redirect(url_for("academy.class_detail", class_id=class_id))


# ---------------------------------------------------------------------------
# Teacher Contracts
# ---------------------------------------------------------------------------


@admin_bp.route("/contracts")
@login_required
@role_required("ADMIN")
def contract_list():
    """List all teacher contracts."""
    from app.application.payroll.services import list_contracts
    from app.infrastructure.database.models import UserModel

    teacher_id = request.args.get("teacher_id", type=int)
    contracts = list_contracts(teacher_user_id=teacher_id)

    teachers = UserModel.query.filter(UserModel.roles.any(name="TEACHER")).all()

    return render_template(
        "admin/contract_list.html",
        contracts=contracts,
        teachers=teachers,
        selected_teacher_id=teacher_id,
    )


@admin_bp.route("/contracts/create", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def contract_create():
    """Create a new teacher contract."""
    from app.application.payroll.services import PayrollError, create_contract
    from app.infrastructure.database.models import AcademyClassModel, UserModel

    teachers = UserModel.query.filter(UserModel.roles.any(name="TEACHER")).all()
    classes = AcademyClassModel.query.filter_by(status="ACTIVE").all()

    if request.method == "POST":
        teacher_user_id = request.form.get("teacher_user_id", type=int)
        class_id = request.form.get("class_id", type=int)
        payment_type = request.form.get("payment_type", "").strip()
        rate = request.form.get("rate", "").strip()
        start_date_str = request.form.get("start_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip()

        if not teacher_user_id or not payment_type or not rate:
            flash("معلم، نوع پرداخت و نرخ الزامی هستند.", "error")
            return render_template(
                "admin/contract_form.html",
                teachers=teachers,
                classes=classes,
            )

        try:
            rate_decimal = Decimal(rate)
        except Exception:
            flash("نرخ پرداخت نامعتبر است.", "error")
            return render_template(
                "admin/contract_form.html",
                teachers=teachers,
                classes=classes,
            )

        from app.utils.date_utils import parse_jalali_date_or_none

        start_date = parse_jalali_date_or_none(start_date_str)
        end_date = parse_jalali_date_or_none(end_date_str)

        try:
            create_contract(
                teacher_user_id=teacher_user_id,
                class_id=class_id if class_id else None,
                payment_type=payment_type,
                rate=rate_decimal,
                start_date=start_date,
                end_date=end_date,
            )
            flash("قرارداد با موفقیت ایجاد شد.", "success")
            return redirect(url_for("admin.contract_list"))
        except PayrollError as e:
            flash(str(e), "error")

    return render_template(
        "admin/contract_form.html",
        teachers=teachers,
        classes=classes,
    )


@admin_bp.route("/contracts/<int:contract_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def contract_edit(contract_id):
    """Edit a teacher contract."""
    from app.application.payroll.services import (
        PayrollError,
        get_contract,
        update_contract,
    )
    from app.infrastructure.database.models import AcademyClassModel, UserModel

    contract = get_contract(contract_id)
    if contract is None:
        flash("قرارداد یافت نشد.", "error")
        return redirect(url_for("admin.contract_list"))

    teachers = UserModel.query.filter(UserModel.roles.any(name="TEACHER")).all()
    classes = AcademyClassModel.query.filter_by(status="ACTIVE").all()

    if request.method == "POST":
        class_id = request.form.get("class_id", type=int)
        payment_type = request.form.get("payment_type", "").strip()
        rate = request.form.get("rate", "").strip()
        is_active = request.form.get("is_active") == "on"
        start_date_str = request.form.get("start_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip()

        if not payment_type or not rate:
            flash("نوع پرداخت و نرخ الزامی هستند.", "error")
            return render_template(
                "admin/contract_form.html",
                contract=contract,
                teachers=teachers,
                classes=classes,
            )

        try:
            rate_decimal = Decimal(rate)
        except Exception:
            flash("نرخ پرداخت نامعتبر است.", "error")
            return render_template(
                "admin/contract_form.html",
                contract=contract,
                teachers=teachers,
                classes=classes,
            )

        from app.utils.date_utils import parse_jalali_date_or_none

        start_date = parse_jalali_date_or_none(start_date_str)
        end_date = parse_jalali_date_or_none(end_date_str)

        try:
            update_contract(
                contract,
                class_id=class_id if class_id else None,
                payment_type=payment_type,
                rate=rate_decimal,
                is_active=is_active,
                start_date=start_date,
                end_date=end_date,
            )
            flash("قرارداد با موفقیت به‌روزرسانی شد.", "success")
            return redirect(url_for("admin.contract_list"))
        except PayrollError as e:
            flash(str(e), "error")

    return render_template(
        "admin/contract_form.html",
        contract=contract,
        teachers=teachers,
        classes=classes,
    )


@admin_bp.route("/contracts/<int:contract_id>/delete", methods=["POST"])
@login_required
@role_required("ADMIN")
def contract_delete(contract_id):
    """Soft-delete a teacher contract."""
    from app.application.payroll.services import delete_contract, get_contract

    contract = get_contract(contract_id)
    if contract is None:
        flash("قرارداد یافت نشد.", "error")
        return redirect(url_for("admin.contract_list"))

    delete_contract(contract)
    flash("قرارداد غیرفعال شد.", "success")
    return redirect(url_for("admin.contract_list"))


# ---------------------------------------------------------------------------
# Payroll Management
# ---------------------------------------------------------------------------


@admin_bp.route("/payroll")
@login_required
@role_required("ADMIN")
def payroll():
    """Payroll dashboard — select month and view teacher payouts."""
    import jdatetime

    from app.application.payroll.services import list_teachers_with_payroll_summary
    from app.utils.date_utils import gregorian_to_jalali

    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)

    if year is None or month is None:
        today_jalali = gregorian_to_jalali(date.today())
        if today_jalali is not None:
            year = today_jalali.year
            month = today_jalali.month
        else:
            year = 1405
            month = 6

    # Convert Jalali month start/end to Gregorian
    try:
        jd_start = jdatetime.date(year, month, 1)
        if month < 12:
            jd_end = jdatetime.date(year, month + 1, 1)
        else:
            jd_end = jdatetime.date(year + 1, 1, 1)
    except ValueError:
        flash("تاریخ نامعتبر است.", "error")
        return render_template(
            "admin/payroll.html", teachers_data=[], year=year, month=month
        )

    from app.utils.date_utils import jalali_to_gregorian

    period_start = jalali_to_gregorian(jd_start)
    period_end = jalali_to_gregorian(jd_end)

    teachers_data = list_teachers_with_payroll_summary(period_start, period_end)

    months = [
        (1, "فروردین"),
        (2, "اردیبهشت"),
        (3, "خرداد"),
        (4, "تیر"),
        (5, "مرداد"),
        (6, "شهریور"),
        (7, "مهر"),
        (8, "آبان"),
        (9, "آذر"),
        (10, "دی"),
        (11, "بهمن"),
        (12, "اسفند"),
    ]

    return render_template(
        "admin/payroll.html",
        teachers_data=teachers_data,
        year=year,
        month=month,
        months=months,
        period_start=period_start,
        period_end=period_end,
    )


@admin_bp.route("/payroll/finalize", methods=["POST"])
@login_required
@role_required("ADMIN")
def payroll_finalize():
    """Finalize payroll for a specific teacher."""
    from app.application.payroll.services import PayrollError, finalize_payroll

    teacher_user_id = request.form.get("teacher_user_id", type=int)
    period_start_str = request.form.get("period_start", "").strip()
    period_end_str = request.form.get("period_end", "").strip()
    deductions = request.form.get("deductions", "0").strip()

    if not teacher_user_id or not period_start_str or not period_end_str:
        flash("اطلاعات ناقص است.", "error")
        return redirect(url_for("admin.payroll"))

    from app.utils.date_utils import parse_jalali_date

    try:
        period_start = parse_jalali_date(period_start_str)
        period_end = parse_jalali_date(period_end_str)
        deductions_decimal = Decimal(deductions) if deductions else Decimal("0")
    except (ValueError, Exception) as e:
        flash(f"خطا در تاریخ: {e}", "error")
        return redirect(url_for("admin.payroll"))

    try:
        finalize_payroll(
            teacher_user_id=teacher_user_id,
            period_start=period_start,
            period_end=period_end,
            deductions=deductions_decimal,
        )
        flash("حقوق با موفقیت محاسبه و ثبت شد.", "success")
    except PayrollError as e:
        flash(str(e), "error")

    # Redirect back with same month params
    import jdatetime

    jd = jdatetime.date.fromgregorian(date=period_start)
    return redirect(url_for("admin.payroll", year=jd.year, month=jd.month))


@admin_bp.route("/payroll/<int:payment_id>/pay", methods=["POST"])
@login_required
@role_required("ADMIN")
def payroll_pay(payment_id):
    """Mark a teacher payment as paid."""
    from app.application.payroll.services import (
        PayrollError,
        get_payment,
        mark_payment_paid,
    )

    payment = get_payment(payment_id)
    if payment is None:
        flash("رکورد پرداخت یافت نشد.", "error")
        return redirect(url_for("admin.payroll"))

    try:
        mark_payment_paid(payment)
        flash("پرداخت با موفقیت ثبت شد.", "success")
    except PayrollError as e:
        flash(str(e), "error")

    import jdatetime

    jd = jdatetime.date.fromgregorian(date=payment.period_start)
    return redirect(url_for("admin.payroll", year=jd.year, month=jd.month))
