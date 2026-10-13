from __future__ import annotations

import csv
import io
from datetime import date, datetime

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.application.assessment import assessment_service
from app.infrastructure.database.models import (
    AcademyClassModel,
    AssessmentModel,
    UserModel,
)
from app.interface.web.decorators import role_required
from app.utils.flash import flash_safe_error

assessment_bp = Blueprint("assessment", __name__, url_prefix="/assessment")


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------


@assessment_bp.route("/admin/all")
@login_required
@role_required("ADMIN")
def admin_assessment_list():
    """List all assessments with filters."""
    class_id = request.args.get("class_id", type=int)
    assessment_type = request.args.get("type", "")
    status = request.args.get("status", "")

    assessments = assessment_service.list_all_assessments(
        class_id=class_id,
        assessment_type=assessment_type or None,
        status=status or None,
    )
    classes = AcademyClassModel.query.order_by(AcademyClassModel.title).all()

    return render_template(
        "assessment/admin_list.html",
        assessments=assessments,
        classes=classes,
        filters={"class_id": class_id, "type": assessment_type, "status": status},
    )


@assessment_bp.route("/admin/create", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def admin_create_assessment():
    """Create a new assessment."""
    if request.method == "POST":
        try:
            scheduled_date = None
            scheduled_date_str = request.form.get("scheduled_date", "")
            if scheduled_date_str:
                scheduled_date = date.fromisoformat(scheduled_date_str)

            scheduled_time = None
            scheduled_time_str = request.form.get("scheduled_time", "")
            if scheduled_time_str:
                scheduled_time = datetime.fromisoformat(scheduled_time_str)

            duration_str = request.form.get("duration_minutes", "")
            duration = int(duration_str) if duration_str else None

            assessment = assessment_service.create_assessment(
                class_id=int(request.form["class_id"]),
                assessment_type=request.form["assessment_type"],
                title=request.form["title"],
                description=request.form.get("description", ""),
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time,
                duration_minutes=duration,
                max_score=float(request.form.get("max_score", 100)),
                passing_score=float(request.form.get("passing_score", 60)),
                penalty_factor=float(request.form.get("penalty_factor", 0)),
                status=request.form.get("status", "DRAFT"),
                created_by=current_user.id,
                notes=request.form.get("notes", ""),
            )
            flash("Assessment created successfully.", "success")
            return redirect(
                url_for(
                    "assessment.admin_assessment_detail", assessment_id=assessment.id
                )
            )
        except assessment_service.AssessmentError as e:
            flash_safe_error(e)

    classes = AcademyClassModel.query.order_by(AcademyClassModel.title).all()
    return render_template("assessment/admin_create.html", classes=classes)


@assessment_bp.route("/admin/<int:assessment_id>")
@login_required
@role_required("ADMIN")
def admin_assessment_detail(assessment_id):
    """View assessment detail with results."""
    assessment = assessment_service.get_assessment(assessment_id)
    if assessment is None:
        flash("Assessment not found.", "error")
        return redirect(url_for("assessment.admin_assessment_list"))

    report = assessment_service.get_assessment_report(assessment_id)
    academy_class = AcademyClassModel.query.get(assessment.class_id)

    return render_template(
        "assessment/admin_detail.html",
        assessment=assessment,
        academy_class=academy_class,
        report=report,
    )


@assessment_bp.route("/admin/<int:assessment_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def admin_edit_assessment(assessment_id):
    """Edit an assessment."""
    assessment = assessment_service.get_assessment(assessment_id)
    if assessment is None:
        flash("Assessment not found.", "error")
        return redirect(url_for("assessment.admin_assessment_list"))

    if request.method == "POST":
        try:
            scheduled_date = None
            scheduled_date_str = request.form.get("scheduled_date", "")
            if scheduled_date_str:
                scheduled_date = date.fromisoformat(scheduled_date_str)

            scheduled_time = None
            scheduled_time_str = request.form.get("scheduled_time", "")
            if scheduled_time_str:
                scheduled_time = datetime.fromisoformat(scheduled_time_str)

            duration_str = request.form.get("duration_minutes", "")
            duration = int(duration_str) if duration_str else None

            assessment_service.update_assessment(
                assessment,
                title=request.form["title"],
                description=request.form.get("description", ""),
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time,
                duration_minutes=duration,
                max_score=float(request.form.get("max_score", 100)),
                passing_score=float(request.form.get("passing_score", 60)),
                notes=request.form.get("notes", ""),
            )
            flash("Assessment updated successfully.", "success")
            return redirect(
                url_for(
                    "assessment.admin_assessment_detail", assessment_id=assessment.id
                )
            )
        except assessment_service.AssessmentError as e:
            flash_safe_error(e)

    return render_template("assessment/admin_edit.html", assessment=assessment)


@assessment_bp.route("/admin/<int:assessment_id>/status", methods=["POST"])
@login_required
@role_required("ADMIN")
def admin_update_status(assessment_id):
    """Update assessment status."""
    assessment = assessment_service.get_assessment(assessment_id)
    if assessment is None:
        flash("Assessment not found.", "error")
        return redirect(url_for("assessment.admin_assessment_list"))

    new_status = request.form.get("status", "")
    try:
        assessment_service.update_assessment_status(assessment, new_status)
        flash(f"Assessment status updated to {new_status}.", "success")
    except assessment_service.AssessmentError as e:
        flash_safe_error(e)

    return redirect(
        url_for("assessment.admin_assessment_detail", assessment_id=assessment.id)
    )


@assessment_bp.route("/admin/<int:assessment_id>/cancel", methods=["POST"])
@login_required
@role_required("ADMIN")
def admin_cancel_assessment(assessment_id):
    """Cancel an assessment."""
    assessment = assessment_service.get_assessment(assessment_id)
    if assessment is None:
        flash("Assessment not found.", "error")
        return redirect(url_for("assessment.admin_assessment_list"))

    try:
        assessment_service.cancel_assessment(assessment)
        flash("Assessment cancelled.", "success")
    except assessment_service.AssessmentError as e:
        flash_safe_error(e)

    return redirect(
        url_for("assessment.admin_assessment_detail", assessment_id=assessment.id)
    )


@assessment_bp.route("/admin/<int:assessment_id>/grade", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def admin_grade_assessment(assessment_id):
    """Bulk grading page for an assessment."""
    assessment = assessment_service.get_assessment(assessment_id)
    if assessment is None:
        flash("Assessment not found.", "error")
        return redirect(url_for("assessment.admin_assessment_list"))

    if request.method == "POST":
        try:
            results_data = _parse_grade_form(request.form)
            assessment_service.record_bulk_results(
                assessment_id=assessment_id,
                results_data=results_data,
                graded_by=current_user.id,
            )
            flash("Grades saved successfully.", "success")
        except assessment_service.AssessmentError as e:
            flash_safe_error(e)
        return redirect(
            url_for("assessment.admin_grade_assessment", assessment_id=assessment.id)
        )

    eligible = assessment_service.get_eligible_enrollments(assessment_id)
    existing_results = assessment_service.get_assessment_results(assessment_id)
    result_map = {r.enrollment_id: r for r in existing_results}

    return render_template(
        "assessment/admin_grade.html",
        assessment=assessment,
        eligible=enrollments_with_students(eligible),
        result_map=result_map,
    )


@assessment_bp.route("/admin/<int:assessment_id>/report")
@login_required
@role_required("ADMIN")
def admin_assessment_report(assessment_id):
    """Assessment report page."""
    try:
        report = assessment_service.get_assessment_report(assessment_id)
    except assessment_service.AssessmentError as e:
        flash_safe_error(e)
        return redirect(url_for("assessment.admin_assessment_list"))

    return render_template("assessment/admin_report.html", report=report)


@assessment_bp.route("/admin/<int:assessment_id>/export")
@login_required
@role_required("ADMIN")
def admin_export_assessment_csv(assessment_id):
    """Export assessment results as CSV."""
    try:
        rows = assessment_service.get_assessment_csv_data(assessment_id)
    except assessment_service.AssessmentError as e:
        flash_safe_error(e)
        return redirect(url_for("assessment.admin_assessment_list"))

    output = io.StringIO()
    output.write("\ufeff")  # BOM for Excel compatibility with Persian
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "student_id",
            "first_name",
            "last_name",
            "national_id",
            "score",
            "max_score",
            "percentage",
            "pass_fail",
            "presence",
            "comments",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=assessment_{assessment_id}_results.csv"
        },
    )


@assessment_bp.route("/admin/student/<int:student_id>/results")
@login_required
@role_required("ADMIN")
def admin_student_results(student_id):
    """View a student's academic results."""
    student = UserModel.query.get(student_id)
    if student is None:
        flash("Student not found.", "error")
        return redirect(url_for("assessment.admin_assessment_list"))

    summary = assessment_service.get_student_academic_summary(student_id)
    return render_template(
        "assessment/admin_student_results.html",
        student=student,
        summary=summary,
    )


@assessment_bp.route("/admin/class/<int:class_id>/report")
@login_required
@role_required("ADMIN")
def admin_class_report(class_id):
    """Class academic summary report."""
    try:
        summary = assessment_service.get_class_academic_summary(class_id)
    except assessment_service.AssessmentError as e:
        flash_safe_error(e)
        return redirect(url_for("assessment.admin_assessment_list"))

    return render_template("assessment/admin_class_report.html", summary=summary)


@assessment_bp.route("/admin/class/<int:class_id>/export")
@login_required
@role_required("ADMIN")
def admin_export_class_csv(class_id):
    """Export class results as CSV."""
    try:
        results = assessment_service.get_class_results(class_id)
    except assessment_service.AssessmentError as e:
        flash_safe_error(e)
        return redirect(url_for("assessment.admin_assessment_list"))

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(
        [
            "Student ID",
            "First Name",
            "Last Name",
            "National ID",
            "Assessment",
            "Score",
            "Max Score",
            "Percentage",
            "Pass/Fail",
        ]
    )

    for r in results:
        student = UserModel.query.get(r.student_user_id)
        profile = student.student_profile if student else None
        assessment = AssessmentModel.query.get(r.assessment_id)

        writer.writerow(
            [
                r.student_user_id,
                profile.first_name if profile else "",
                profile.last_name if profile else "",
                profile.national_id if profile else "",
                assessment.title if assessment else "",
                float(r.score) if r.score is not None else "",
                float(r.max_score),
                float(r.percentage) if r.percentage is not None else "",
                r.pass_fail,
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=class_{class_id}_results.csv"
        },
    )


# ---------------------------------------------------------------------------
# Teacher routes
# ---------------------------------------------------------------------------


@assessment_bp.route("/teacher/my-classes")
@login_required
@role_required("TEACHER")
def teacher_my_classes():
    """List teacher's assigned classes."""
    classes = (
        AcademyClassModel.query.filter_by(teacher_user_id=current_user.id)
        .order_by(AcademyClassModel.title)
        .all()
    )
    return render_template("assessment/teacher_classes.html", classes=classes)


@assessment_bp.route("/teacher/class/<int:class_id>/assessments")
@login_required
@role_required("TEACHER")
def teacher_class_assessments(class_id):
    """List assessments for a teacher's class."""
    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        flash("Class not found.", "error")
        return redirect(url_for("assessment.teacher_my_classes"))

    if not assessment_service.is_teacher_of_class(current_user.id, class_id):
        abort(403)

    assessments = assessment_service.list_class_assessments(class_id)
    return render_template(
        "assessment/teacher_class_assessments.html",
        academy_class=academy_class,
        assessments=assessments,
    )


@assessment_bp.route("/teacher/assessment/<int:assessment_id>")
@login_required
@role_required("TEACHER")
def teacher_assessment_detail(assessment_id):
    """View assessment detail (teacher)."""
    assessment = assessment_service.get_assessment(assessment_id)
    if assessment is None:
        flash("Assessment not found.", "error")
        return redirect(url_for("assessment.teacher_my_classes"))

    if not assessment_service.is_teacher_of_class(current_user.id, assessment.class_id):
        abort(403)

    report = assessment_service.get_assessment_report(assessment_id)
    academy_class = AcademyClassModel.query.get(assessment.class_id)

    return render_template(
        "assessment/teacher_detail.html",
        assessment=assessment,
        academy_class=academy_class,
        report=report,
    )


@assessment_bp.route(
    "/teacher/assessment/<int:assessment_id>/grade", methods=["GET", "POST"]
)
@login_required
@role_required("TEACHER")
def teacher_grade_assessment(assessment_id):
    """Bulk grading page (teacher)."""
    assessment = assessment_service.get_assessment(assessment_id)
    if assessment is None:
        flash("Assessment not found.", "error")
        return redirect(url_for("assessment.teacher_my_classes"))

    if not assessment_service.is_teacher_of_class(current_user.id, assessment.class_id):
        abort(403)

    if request.method == "POST":
        try:
            results_data = _parse_grade_form(request.form)
            assessment_service.record_bulk_results(
                assessment_id=assessment_id,
                results_data=results_data,
                graded_by=current_user.id,
            )
            flash("Grades saved successfully.", "success")
        except assessment_service.AssessmentError as e:
            flash_safe_error(e)
        return redirect(
            url_for("assessment.teacher_grade_assessment", assessment_id=assessment.id)
        )

    eligible = assessment_service.get_eligible_enrollments(assessment_id)
    existing_results = assessment_service.get_assessment_results(assessment_id)
    result_map = {r.enrollment_id: r for r in existing_results}

    return render_template(
        "assessment/teacher_grade.html",
        assessment=assessment,
        eligible=enrollments_with_students(eligible),
        result_map=result_map,
    )


@assessment_bp.route(
    "/teacher/assessment/<int:assessment_id>/result/<int:result_id>/edit",
    methods=["GET", "POST"],
)
@login_required
@role_required("TEACHER")
def teacher_edit_result(assessment_id, result_id):
    """Edit a single result (teacher)."""
    assessment = assessment_service.get_assessment(assessment_id)
    if assessment is None:
        flash("Assessment not found.", "error")
        return redirect(url_for("assessment.teacher_my_classes"))

    if not assessment_service.is_teacher_of_class(current_user.id, assessment.class_id):
        abort(403)

    result = assessment_service.get_result(result_id)
    if result is None or result.assessment_id != assessment_id:
        flash("Result not found.", "error")
        return redirect(
            url_for("assessment.teacher_assessment_detail", assessment_id=assessment_id)
        )

    if request.method == "POST":
        try:
            score_str = request.form.get("score", "")
            score = float(score_str) if score_str else None
            assessment_service.update_result(
                result_id,
                score=score,
                presence_status=request.form.get("presence_status", "PRESENT"),
                comments=request.form.get("comments", ""),
                graded_by=current_user.id,
            )
            flash("Result updated.", "success")
        except assessment_service.AssessmentError as e:
            flash_safe_error(e)
        return redirect(
            url_for("assessment.teacher_assessment_detail", assessment_id=assessment_id)
        )

    return render_template(
        "assessment/teacher_edit_result.html",
        assessment=assessment,
        result=result,
    )


@assessment_bp.route("/teacher/assessment/<int:assessment_id>/history")
@login_required
@role_required("TEACHER")
def teacher_grade_history(assessment_id):
    """View grading history for an assessment."""
    assessment = assessment_service.get_assessment(assessment_id)
    if assessment is None:
        flash("Assessment not found.", "error")
        return redirect(url_for("assessment.teacher_my_classes"))

    if not assessment_service.is_teacher_of_class(current_user.id, assessment.class_id):
        abort(403)

    results = assessment_service.get_assessment_results(assessment_id)
    history_data = []
    for r in results:
        history = assessment_service.get_grade_history(r.id)
        if history:
            student = UserModel.query.get(r.student_user_id)
            history_data.append(
                {
                    "result": r,
                    "student": student,
                    "history": history,
                }
            )

    return render_template(
        "assessment/teacher_history.html",
        assessment=assessment,
        history_data=history_data,
    )


# ---------------------------------------------------------------------------
# Student routes
# ---------------------------------------------------------------------------


@assessment_bp.route("/student/my-assessments")
@login_required
@role_required("STUDENT")
def student_my_assessments():
    """View student's own assessment results."""
    summary = assessment_service.get_student_academic_summary(current_user.id)
    classes = assessment_service.get_student_enrolled_classes(current_user.id)
    return render_template(
        "assessment/student_assessments.html",
        summary=summary,
        classes=classes,
    )


@assessment_bp.route("/student/class/<int:class_id>/results")
@login_required
@role_required("STUDENT")
def student_class_results(class_id):
    """View student's results for a specific class."""
    if not assessment_service.is_student_enrolled(current_user.id, class_id):
        flash("You are not enrolled in this class.", "error")
        return redirect(url_for("assessment.student_my_assessments"))

    results = assessment_service.get_student_class_results(current_user.id, class_id)
    academy_class = AcademyClassModel.query.get(class_id)

    # Get enrollment for transcript link
    from app.infrastructure.database.models import EnrollmentModel

    enrollment = EnrollmentModel.query.filter_by(
        student_user_id=current_user.id,
        class_id=class_id,
        status="APPROVED",
    ).first()

    return render_template(
        "assessment/student_class_results.html",
        results=results,
        academy_class=academy_class,
        enrollment=enrollment,
    )


@assessment_bp.route("/student/result/<int:result_id>")
@login_required
@role_required("STUDENT")
def student_result_detail(result_id):
    """View result detail (student)."""
    result = assessment_service.get_result(result_id)
    if result is None or result.student_user_id != current_user.id:
        flash("Result not found.", "error")
        return redirect(url_for("assessment.student_my_assessments"))

    assessment = assessment_service.get_assessment(result.assessment_id)
    history = assessment_service.get_grade_history(result.id)

    return render_template(
        "assessment/student_result_detail.html",
        result=result,
        assessment=assessment,
        history=history,
    )


@assessment_bp.route("/student/export")
@login_required
@role_required("STUDENT")
def student_export_csv():
    """Export student's results as CSV."""
    rows = assessment_service.get_student_csv_data(current_user.id)

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "assessment_title",
            "assessment_type",
            "class_title",
            "score",
            "max_score",
            "percentage",
            "pass_fail",
            "presence",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=my_results.csv"},
    )


# ---------------------------------------------------------------------------
# Parent routes
# ---------------------------------------------------------------------------


@assessment_bp.route("/parent/overview")
@login_required
@role_required("PARENT")
def parent_overview():
    """Parent overview of all linked children's results."""
    children = assessment_service.get_parent_children(current_user.id)
    children_data = []
    for child in children:
        summary = assessment_service.get_student_academic_summary(child.id)
        children_data.append({"child": child, "summary": summary})

    return render_template(
        "assessment/parent_overview.html",
        children_data=children_data,
    )


@assessment_bp.route("/parent/child/<int:student_id>/results")
@login_required
@role_required("PARENT")
def parent_child_results(student_id):
    """View a specific child's results."""
    if not assessment_service.is_parent_of_student(current_user.id, student_id):
        abort(403)

    student = UserModel.query.get(student_id)
    if student is None:
        flash("Student not found.", "error")
        return redirect(url_for("assessment.parent_overview"))

    summary = assessment_service.get_student_academic_summary(student_id)
    return render_template(
        "assessment/parent_child_results.html",
        student=student,
        summary=summary,
    )


@assessment_bp.route("/parent/child/<int:student_id>/result/<int:result_id>")
@login_required
@role_required("PARENT")
def parent_result_detail(student_id, result_id):
    """View a specific result for a linked child."""
    if not assessment_service.is_parent_of_student(current_user.id, student_id):
        abort(403)

    result = assessment_service.get_result(result_id)
    if result is None or result.student_user_id != student_id:
        flash("Result not found.", "error")
        return redirect(url_for("assessment.parent_overview"))

    assessment = assessment_service.get_assessment(result.assessment_id)

    return render_template(
        "assessment/parent_result_detail.html",
        result=result,
        assessment=assessment,
        student_id=student_id,
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


def _parse_grade_form(form) -> list[dict]:
    """Parse the bulk grading form data.

    Form fields are named: grade_<enrollment_id>_score, grade_<enrollment_id>_presence,
    grade_<enrollment_id>_comments
    """
    data = []
    processed = set()

    for key in form:
        if key.startswith("grade_") and key.endswith("_score"):
            enrollment_id_str = key[len("grade_") : -len("_score")]
            try:
                enrollment_id = int(enrollment_id_str)
            except ValueError:
                continue

            if enrollment_id in processed:
                continue
            processed.add(enrollment_id)

            score_str = form.get(key, "")
            score = float(score_str) if score_str else None
            presence = form.get(f"grade_{enrollment_id}_presence", "PRESENT")
            comments = form.get(f"grade_{enrollment_id}_comments", "")

            # Parse wrong_count for negative marking
            wrong_count_str = form.get(f"grade_{enrollment_id}_wrong_count", "")
            wrong_count = int(wrong_count_str) if wrong_count_str else None

            data.append(
                {
                    "enrollment_id": enrollment_id,
                    "score": score,
                    "wrong_count": wrong_count,
                    "presence_status": presence,
                    "comments": comments,
                }
            )

    return data


# ---------------------------------------------------------------------------
# Student enrollment check helper (imported from activity service pattern)
# ---------------------------------------------------------------------------


def _is_student_enrolled(student_user_id: int, class_id: int) -> bool:
    """Check if a student has an approved enrollment in a class."""
    from app.infrastructure.database.models import EnrollmentModel

    return (
        EnrollmentModel.query.filter_by(
            student_user_id=student_user_id,
            class_id=class_id,
            status="APPROVED",
        ).first()
        is not None
    )


# ---------------------------------------------------------------------------
# P21 — Grading Template Management (Admin)
# ---------------------------------------------------------------------------


@assessment_bp.route(
    "/admin/class/<int:class_id>/grading-template", methods=["GET", "POST"]
)
@login_required
@role_required("ADMIN")
def admin_grading_template(class_id: int):
    """Create or edit grading template for a class."""
    academy_class = AcademyClassModel.query.get_or_404(class_id)

    existing_template = assessment_service.get_class_grading_template(class_id)

    if request.method == "POST":
        try:
            title = request.form.get("title", "").strip()
            if not title:
                flash("عنوان فرمول ارزیابی الزامی است.", "error")
                return redirect(
                    url_for("assessment.admin_grading_template", class_id=class_id)
                )

            # Parse components from form
            components = []
            types = request.form.getlist("component_type[]")
            weights = request.form.getlist("component_weight[]")

            for atype, weight_str in zip(types, weights):
                if atype and weight_str:
                    try:
                        weight = float(weight_str)
                    except ValueError:
                        continue
                    components.append({"assessment_type": atype, "weight": weight})

            if existing_template:
                assessment_service.update_grading_template(
                    existing_template.id, title=title, components=components
                )
                flash("فرمول ارزیابی با موفقیت به‌روزرسانی شد.", "success")
            else:
                assessment_service.create_grading_template(
                    class_id=class_id, title=title, components=components
                )
                flash("فرمول ارزیابی با موفقیت ایجاد شد.", "success")

            return redirect(
                url_for("assessment.admin_grading_template", class_id=class_id)
            )

        except assessment_service.AssessmentError as e:
            flash_safe_error(e)

    return render_template(
        "assessment/admin_grading_template.html",
        academy_class=academy_class,
        template=existing_template,
    )


@assessment_bp.route("/admin/class/<int:class_id>/grading-template/view")
@login_required
@role_required("ADMIN")
def admin_grading_template_view(class_id: int):
    """View grading template for a class."""
    academy_class = AcademyClassModel.query_or_404(class_id)
    template = assessment_service.get_class_grading_template(class_id)

    return render_template(
        "assessment/admin_grading_template_view.html",
        academy_class=academy_class,
        template=template,
    )


# ---------------------------------------------------------------------------
# P21 — Transcript (Student, Parent, Admin, Teacher)
# ---------------------------------------------------------------------------


@assessment_bp.route("/student/<int:enrollment_id>/transcript")
@login_required
def student_transcript(enrollment_id: int):
    """Generate and display transcript for a student in a class."""
    from app.infrastructure.database.models import EnrollmentModel

    enrollment = EnrollmentModel.query.get_or_404(enrollment_id)

    # Authorization: student can view own, parent can view children, admin can
    # view all. Teachers may only view transcripts for classes they teach —
    # a bare TEACHER role check would let any teacher read any enrollment.
    user_id = current_user.id
    is_admin = any(r.name == "ADMIN" for r in current_user.roles)
    is_teacher_of_class = assessment_service.is_teacher_of_class(
        user_id, enrollment.class_id
    )
    is_student_owner = enrollment.student_user_id == user_id
    is_parent_linked = assessment_service.is_parent_of_student(
        user_id, enrollment.student_user_id
    )

    if not (is_admin or is_teacher_of_class or is_student_owner or is_parent_linked):
        abort(403)

    try:
        transcript_data = assessment_service.get_transcript_data(enrollment_id)
    except assessment_service.AssessmentError as e:
        flash_safe_error(e)
        return redirect(url_for("assessment.student_my_assessments"))

    return render_template(
        "assessment/transcript.html",
        transcript=transcript_data,
        enrollment=enrollment,
    )
