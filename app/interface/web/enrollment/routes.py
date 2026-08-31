from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.application.enrollment.enrollment_service import (
    EnrollmentError,
    admin_enroll_student,
    approve_enrollment,
    cancel_enrollment,
    get_class_available_capacity,
    get_enrollment,
    get_schedule_conflict_details,
    has_schedule_conflict,
    list_all_pending_enrollments,
    list_enrollments_by_class,
    list_enrollments_by_student,
    reject_enrollment,
    request_enrollment,
)
from app.extensions import db
from app.infrastructure.database.models import (
    AcademyClassModel,
    CourseModel,
    UserModel,
)
from app.interface.web.decorators import role_required

enrollment_bp = Blueprint("enrollment", __name__, url_prefix="/enrollment")


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------


@enrollment_bp.route("/admin/all")
@login_required
@role_required("ADMIN")
def admin_enrollment_list():
    """List all enrollments."""
    class_id = request.args.get("class_id", type=int)
    status_filter = request.args.get("status", "")

    if class_id:
        enrollments = list_enrollments_by_class(class_id)
    elif status_filter == "PENDING":
        enrollments = list_all_pending_enrollments()
    else:
        from app.infrastructure.database.models import EnrollmentModel

        enrollments = EnrollmentModel.query.order_by(
            EnrollmentModel.created_at.desc()
        ).all()

    classes = AcademyClassModel.query.order_by(AcademyClassModel.title).all()
    return render_template(
        "enrollment/admin_list.html",
        enrollments=enrollments,
        classes=classes,
        selected_class_id=class_id,
        selected_status=status_filter,
    )


@enrollment_bp.route("/admin/pending")
@login_required
@role_required("ADMIN")
def admin_pending_list():
    """List all pending enrollment requests."""
    pending = list_all_pending_enrollments()
    return render_template(
        "enrollment/admin_pending.html",
        enrollments=pending,
    )


@enrollment_bp.route("/admin/<int:enrollment_id>")
@login_required
@role_required("ADMIN")
def admin_enrollment_detail(enrollment_id):
    """View enrollment details."""
    enrollment = get_enrollment(enrollment_id)
    if enrollment is None:
        flash("Enrollment not found.", "error")
        return redirect(url_for("enrollment.admin_enrollment_list"))

    academy_class = AcademyClassModel.query.get(enrollment.class_id)
    student = UserModel.query.get(enrollment.student_user_id)
    return render_template(
        "enrollment/admin_detail.html",
        enrollment=enrollment,
        academy_class=academy_class,
        student=student,
    )


@enrollment_bp.route("/admin/enroll", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def admin_enroll():
    """Admin directly enroll a student in a class."""
    if request.method == "POST":
        try:
            student_user_id = int(request.form["student_user_id"])
            class_id = int(request.form["class_id"])
            auto_approve = request.form.get("auto_approve") == "on"
            force = request.form.get("force") == "on"

            if not force:
                conflicts = get_schedule_conflict_details(student_user_id, class_id)
                if conflicts:
                    students = UserModel.query.filter(
                        UserModel.roles.any(name="STUDENT")
                    ).all()
                    classes = (
                        AcademyClassModel.query.filter(
                            AcademyClassModel.status.in_(["PLANNED", "ACTIVE"])
                        )
                        .order_by(AcademyClassModel.title)
                        .all()
                    )
                    return render_template(
                        "enrollment/admin_enroll_form.html",
                        students=students,
                        classes=classes,
                        conflicts=conflicts,
                        conflict_student_id=student_user_id,
                        conflict_class_id=class_id,
                        auto_approve=auto_approve,
                    )

            enrollment = admin_enroll_student(
                student_user_id=student_user_id,
                class_id=class_id,
                auto_approve=auto_approve,
            )
            flash("Student enrolled successfully.", "success")
            return redirect(
                url_for(
                    "enrollment.admin_enrollment_detail", enrollment_id=enrollment.id
                )
            )
        except EnrollmentError as e:
            flash(str(e), "error")

    students = UserModel.query.filter(UserModel.roles.any(name="STUDENT")).all()
    classes = (
        AcademyClassModel.query.filter(
            AcademyClassModel.status.in_(["PLANNED", "ACTIVE"])
        )
        .order_by(AcademyClassModel.title)
        .all()
    )
    return render_template(
        "enrollment/admin_enroll_form.html",
        students=students,
        classes=classes,
    )


@enrollment_bp.route("/admin/<int:enrollment_id>/approve", methods=["POST"])
@login_required
@role_required("ADMIN")
def admin_approve(enrollment_id):
    """Approve a pending enrollment."""
    enrollment = get_enrollment(enrollment_id)
    if enrollment is None:
        flash("Enrollment not found.", "error")
        return redirect(url_for("enrollment.admin_enrollment_list"))

    try:
        approve_enrollment(enrollment)
        flash("Enrollment approved.", "success")
    except EnrollmentError as e:
        flash(str(e), "error")

    return redirect(
        url_for("enrollment.admin_enrollment_detail", enrollment_id=enrollment_id)
    )


@enrollment_bp.route("/admin/<int:enrollment_id>/approve-activate", methods=["POST"])
@login_required
@role_required("ADMIN")
def admin_approve_activate(enrollment_id):
    """Approve a public enrollment and activate the user account."""
    enrollment = get_enrollment(enrollment_id)
    if enrollment is None:
        flash("Enrollment not found.", "error")
        return redirect(url_for("enrollment.admin_enrollment_list"))

    try:
        from app.application.enrollment.public_enrollment_service import (
            approve_and_activate_enrollment,
        )

        approve_and_activate_enrollment(enrollment)
        flash("Enrollment approved and account activated.", "success")
    except Exception as e:
        flash(str(e), "error")

    return redirect(
        url_for("enrollment.admin_enrollment_detail", enrollment_id=enrollment_id)
    )


@enrollment_bp.route("/admin/<int:enrollment_id>/reject", methods=["POST"])
@login_required
@role_required("ADMIN")
def admin_reject(enrollment_id):
    """Reject a pending enrollment."""
    enrollment = get_enrollment(enrollment_id)
    if enrollment is None:
        flash("Enrollment not found.", "error")
        return redirect(url_for("enrollment.admin_enrollment_list"))

    try:
        reject_enrollment(enrollment)
        flash("Enrollment rejected.", "success")
    except EnrollmentError as e:
        flash(str(e), "error")

    return redirect(
        url_for("enrollment.admin_enrollment_detail", enrollment_id=enrollment_id)
    )


@enrollment_bp.route("/admin/<int:enrollment_id>/cancel", methods=["POST"])
@login_required
@role_required("ADMIN")
def admin_cancel(enrollment_id):
    """Cancel an enrollment."""
    enrollment = get_enrollment(enrollment_id)
    if enrollment is None:
        flash("Enrollment not found.", "error")
        return redirect(url_for("enrollment.admin_enrollment_list"))

    try:
        cancel_enrollment(enrollment)
        flash("Enrollment cancelled.", "success")
    except EnrollmentError as e:
        flash(str(e), "error")

    return redirect(
        url_for("enrollment.admin_enrollment_detail", enrollment_id=enrollment_id)
    )


# ---------------------------------------------------------------------------
# Excel Import
# ---------------------------------------------------------------------------


@enrollment_bp.route("/admin/import/students", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def admin_import_students():
    """Bulk import students from an Excel file."""
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("لطفاً یک فایل انتخاب کنید.", "error")
            return render_template("enrollment/admin_import.html")

        if not file.filename.endswith((".xlsx", ".xls")):
            flash("فرمت فایل نامعتبر است. فقط فایل .xlsx پذیرفته می‌شود.", "error")
            return render_template("enrollment/admin_import.html")

        try:
            from app.application.enrollment.excel_service import (
                ExcelImportError,
                parse_excel_file,
            )

            result = parse_excel_file(file.read())

            if result.total_rows == 0:
                flash("فایل خالی است.", "error")
                return render_template("enrollment/admin_import.html")

            return render_template(
                "enrollment/admin_import_result.html",
                result=result,
            )
        except ExcelImportError as e:
            flash(str(e), "error")
        except Exception as e:
            db.session.rollback()
            flash(f"خطا در پردازش فایل: {e}", "error")

    return render_template("enrollment/admin_import.html")


# ---------------------------------------------------------------------------
# Student routes
# ---------------------------------------------------------------------------


@enrollment_bp.route("/student/classes")
@login_required
@role_required("STUDENT")
def student_available_classes():
    """List available classes for students."""
    classes = (
        AcademyClassModel.query.filter(
            AcademyClassModel.status.in_(["PLANNED", "ACTIVE"])
        )
        .order_by(AcademyClassModel.start_date)
        .all()
    )

    my_enrollments = list_enrollments_by_student(current_user.id)
    enrolled_class_ids = {
        e.class_id for e in my_enrollments if e.status in ("PENDING", "APPROVED")
    }

    return render_template(
        "enrollment/student_classes.html",
        classes=classes,
        enrolled_class_ids=enrolled_class_ids,
    )


@enrollment_bp.route("/student/classes/<int:class_id>")
@login_required
@role_required("STUDENT")
def student_class_detail(class_id):
    """View class details and request enrollment."""
    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        flash("Class not found.", "error")
        return redirect(url_for("enrollment.student_available_classes"))

    course = CourseModel.query.get(academy_class.course_id)
    teacher = None
    if academy_class.teacher_user_id:
        teacher = UserModel.query.get(academy_class.teacher_user_id)

    available_capacity = get_class_available_capacity(academy_class)

    existing_enrollment = get_enrollment_by_student_class(current_user.id, class_id)

    conflicts = has_schedule_conflict(current_user.id, class_id)

    return render_template(
        "enrollment/student_class_detail.html",
        academy_class=academy_class,
        course=course,
        teacher=teacher,
        available_capacity=available_capacity,
        existing_enrollment=existing_enrollment,
        conflicts=conflicts,
    )


@enrollment_bp.route("/student/classes/<int:class_id>/request", methods=["POST"])
@login_required
@role_required("STUDENT")
def student_request_enrollment(class_id):
    """Request enrollment in a class."""
    try:
        request_enrollment(
            student_user_id=current_user.id,
            class_id=class_id,
        )
        flash("Enrollment request submitted.", "success")
    except EnrollmentError as e:
        flash(str(e), "error")

    return redirect(url_for("enrollment.student_class_detail", class_id=class_id))


@enrollment_bp.route("/student/my-enrollments")
@login_required
@role_required("STUDENT")
def student_my_enrollments():
    """List student's own enrollments."""
    enrollments = list_enrollments_by_student(current_user.id)
    return render_template(
        "enrollment/student_my_enrollments.html",
        enrollments=enrollments,
    )


@enrollment_bp.route("/student/<int:enrollment_id>/cancel", methods=["POST"])
@login_required
@role_required("STUDENT")
def student_cancel(enrollment_id):
    """Cancel own enrollment."""
    enrollment = get_enrollment(enrollment_id)
    if enrollment is None:
        flash("Enrollment not found.", "error")
        return redirect(url_for("enrollment.student_my_enrollments"))

    if enrollment.student_user_id != current_user.id:
        flash("You can only cancel your own enrollments.", "error")
        return redirect(url_for("enrollment.student_my_enrollments"))

    try:
        cancel_enrollment(enrollment)
        flash("Enrollment cancelled.", "success")
    except EnrollmentError as e:
        flash(str(e), "error")

    return redirect(url_for("enrollment.student_my_enrollments"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_enrollment_by_student_class(student_user_id: int, class_id: int):
    """Get enrollment for a student in a class."""
    from app.infrastructure.database.models import EnrollmentModel

    return EnrollmentModel.query.filter_by(
        student_user_id=student_user_id,
        class_id=class_id,
    ).first()
