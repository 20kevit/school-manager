from __future__ import annotations

import os
from datetime import datetime

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.application.activity.activity_service import (
    ActivityError,
    compute_activity_submissions_summary,
    create_activity,
    deactivate_activity,
    get_activity,
    get_all_submissions_for_activity,
    get_class_enrolled_students,
    get_student_enrolled_classes,
    get_submission,
    get_submission_history,
    grade_submission,
    is_student_enrolled,
    is_teacher_of_class,
    list_activities_by_class,
    list_activities_by_class_all,
    list_activities_by_course,
    return_submission,
    submit_activity,
    update_activity,
)
from app.application.file_management.file_service import (
    FileError,
    get_entity_files,
    get_file_stream,
    upload_file,
)
from app.infrastructure.database.models import (
    AcademyClassModel,
    ActivityModel,
    CourseModel,
    SessionModel,
    StoredFileModel,
    UserModel,
)
from app.interface.web.decorators import role_required

activity_bp = Blueprint("activity", __name__, url_prefix="/activity")


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------


@activity_bp.route("/admin/all")
@login_required
@role_required("ADMIN")
def admin_activity_list():
    """List all activities across classes."""
    class_id = request.args.get("class_id", type=int)
    course_id = request.args.get("course_id", type=int)

    if class_id:
        activities = list_activities_by_class_all(class_id)
    elif course_id:
        activities = list_activities_by_course(course_id)
    else:
        activities = (
            ActivityModel.query.filter_by(is_active=True)
            .order_by(ActivityModel.sort_order)
            .limit(100)
            .all()
        )

    classes = AcademyClassModel.query.order_by(AcademyClassModel.title).all()
    courses = CourseModel.query.order_by(CourseModel.title).all()

    return render_template(
        "activity/admin_list.html",
        activities=activities,
        classes=classes,
        courses=courses,
        selected_class_id=class_id,
        selected_course_id=course_id,
    )


@activity_bp.route("/admin/create", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def admin_create_activity():
    """Create a new activity."""
    if request.method == "POST":
        try:
            activity = _create_activity_from_form(request.form)
            flash("فعالیت با موفقیت ایجاد شد.", "success")
            return redirect(
                url_for("activity.admin_activity_detail", activity_id=activity.id)
            )
        except ActivityError as e:
            flash(str(e), "error")

    classes = AcademyClassModel.query.order_by(AcademyClassModel.title).all()
    courses = CourseModel.query.order_by(CourseModel.title).all()
    sessions = SessionModel.query.order_by(
        SessionModel.class_id, SessionModel.session_number
    ).all()

    return render_template(
        "activity/admin_form.html",
        classes=classes,
        courses=courses,
        sessions=sessions,
        activity=None,
    )


@activity_bp.route("/admin/<int:activity_id>")
@login_required
@role_required("ADMIN")
def admin_activity_detail(activity_id):
    """View activity details with submission overview."""
    activity = get_activity(activity_id)
    if activity is None:
        flash("فعالیت یافت نشد.", "error")
        return redirect(url_for("activity.admin_activity_list"))

    submissions = []
    summary = {}
    students_map = {}

    if activity.class_id is not None:
        submissions = get_all_submissions_for_activity(activity_id)
        summary = compute_activity_submissions_summary(activity_id)

        enrolled = get_class_enrolled_students(activity.class_id)
        students_map = {
            e.student_user_id: UserModel.query.get(e.student_user_id) for e in enrolled
        }

    return render_template(
        "activity/admin_detail.html",
        activity=activity,
        submissions=submissions,
        summary=summary,
        students_map=students_map,
    )


@activity_bp.route("/admin/<int:activity_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def admin_edit_activity(activity_id):
    """Edit an activity."""
    activity = get_activity(activity_id)
    if activity is None:
        flash("فعالیت یافت نشد.", "error")
        return redirect(url_for("activity.admin_activity_list"))

    if request.method == "POST":
        try:
            _update_activity_from_form(activity, request.form)
            flash("فعالیت با موفقیت به‌روزرسانی شد.", "success")
            return redirect(
                url_for("activity.admin_activity_detail", activity_id=activity.id)
            )
        except ActivityError as e:
            flash(str(e), "error")

    classes = AcademyClassModel.query.order_by(AcademyClassModel.title).all()
    courses = CourseModel.query.order_by(CourseModel.title).all()
    sessions = SessionModel.query.order_by(
        SessionModel.class_id, SessionModel.session_number
    ).all()

    return render_template(
        "activity/admin_form.html",
        classes=classes,
        courses=courses,
        sessions=sessions,
        activity=activity,
    )


@activity_bp.route("/admin/<int:activity_id>/deactivate", methods=["POST"])
@login_required
@role_required("ADMIN")
def admin_deactivate_activity(activity_id):
    """Deactivate an activity."""
    activity = get_activity(activity_id)
    if activity is None:
        flash("فعالیت یافت نشد.", "error")
        return redirect(url_for("activity.admin_activity_list"))

    deactivate_activity(activity)
    flash("فعالیت غیرفعال شد.", "success")
    return redirect(url_for("activity.admin_activity_list"))


@activity_bp.route("/admin/submission/<int:submission_id>")
@login_required
@role_required("ADMIN")
def admin_submission_detail(submission_id):
    """View a submission detail (admin)."""
    submission = get_submission(submission_id)
    if submission is None:
        flash("ارسال یافت نشد.", "error")
        return redirect(url_for("activity.admin_activity_list"))

    activity = get_activity(submission.activity_id)
    student = UserModel.query.get(submission.student_user_id)
    files = get_entity_files("activity_submission", submission_id)

    return render_template(
        "activity/admin_submission.html",
        submission=submission,
        activity=activity,
        student=student,
        files=files,
    )


@activity_bp.route("/admin/submission/<int:submission_id>/grade", methods=["POST"])
@login_required
@role_required("ADMIN")
def admin_grade_submission(submission_id):
    """Grade a submission (admin)."""
    submission = get_submission(submission_id)
    if submission is None:
        flash("ارسال یافت نشد.", "error")
        return redirect(url_for("activity.admin_activity_list"))

    try:
        score = float(request.form.get("score", 0))
        feedback = request.form.get("feedback", "")
        grade_submission(submission, score, feedback, graded_by=current_user.id)
        flash("ارسال نمره‌گذاری شد.", "success")
    except (ActivityError, ValueError) as e:
        flash(str(e), "error")

    return redirect(
        url_for("activity.admin_submission_detail", submission_id=submission_id)
    )


@activity_bp.route("/admin/submission/<int:submission_id>/return", methods=["POST"])
@login_required
@role_required("ADMIN")
def admin_return_submission(submission_id):
    """Return a submission for correction (admin)."""
    submission = get_submission(submission_id)
    if submission is None:
        flash("ارسال یافت نشد.", "error")
        return redirect(url_for("activity.admin_activity_list"))

    feedback = request.form.get("feedback", "")
    return_submission(submission, feedback, graded_by=current_user.id)
    flash("ارسال برای اصلاح بازگردانده شد.", "success")

    return redirect(
        url_for("activity.admin_submission_detail", submission_id=submission_id)
    )


# ---------------------------------------------------------------------------
# Teacher routes
# ---------------------------------------------------------------------------


@activity_bp.route("/teacher/my-classes")
@login_required
@role_required("TEACHER")
def teacher_my_classes():
    """List teacher's assigned classes."""
    classes = (
        AcademyClassModel.query.filter_by(teacher_user_id=current_user.id)
        .order_by(AcademyClassModel.title)
        .all()
    )
    return render_template("activity/teacher_classes.html", classes=classes)


@activity_bp.route("/teacher/class/<int:class_id>/activities")
@login_required
@role_required("TEACHER")
def teacher_class_activities(class_id):
    """List activities for a teacher's class."""
    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        flash("کلاس یافت نشد.", "error")
        return redirect(url_for("activity.teacher_my_classes"))

    if not is_teacher_of_class(current_user.id, class_id):
        abort(403)

    activities = list_activities_by_class_all(class_id)
    sessions = (
        SessionModel.query.filter_by(class_id=class_id)
        .order_by(SessionModel.session_number)
        .all()
    )

    return render_template(
        "activity/teacher_class_activities.html",
        academy_class=academy_class,
        activities=activities,
        sessions=sessions,
    )


@activity_bp.route("/teacher/class/<int:class_id>/create", methods=["GET", "POST"])
@login_required
@role_required("TEACHER")
def teacher_create_activity(class_id):
    """Create an activity for a teacher's class."""
    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        flash("کلاس یافت نشد.", "error")
        return redirect(url_for("activity.teacher_my_classes"))

    if not is_teacher_of_class(current_user.id, class_id):
        abort(403)

    if request.method == "POST":
        try:
            _create_activity_from_form(request.form, class_id=class_id)
            flash("فعالیت با موفقیت ایجاد شد.", "success")
            return redirect(
                url_for("activity.teacher_class_activities", class_id=class_id)
            )
        except ActivityError as e:
            flash(str(e), "error")

    sessions = (
        SessionModel.query.filter_by(class_id=class_id)
        .order_by(SessionModel.session_number)
        .all()
    )

    return render_template(
        "activity/teacher_form.html",
        academy_class=academy_class,
        sessions=sessions,
        activity=None,
    )


@activity_bp.route("/teacher/<int:activity_id>")
@login_required
@role_required("TEACHER")
def teacher_activity_detail(activity_id):
    """View activity details and submissions (teacher)."""
    activity = get_activity(activity_id)
    if activity is None:
        flash("فعالیت یافت نشد.", "error")
        return redirect(url_for("activity.teacher_my_classes"))

    if activity.class_id is None or not is_teacher_of_class(
        current_user.id, activity.class_id
    ):
        abort(403)

    academy_class = AcademyClassModel.query.get(activity.class_id)
    submissions = get_all_submissions_for_activity(activity_id)
    summary = compute_activity_submissions_summary(activity_id)

    enrolled = get_class_enrolled_students(activity.class_id)
    students_map = {
        e.student_user_id: UserModel.query.get(e.student_user_id) for e in enrolled
    }

    return render_template(
        "activity/teacher_detail.html",
        activity=activity,
        academy_class=academy_class,
        submissions=submissions,
        summary=summary,
        students_map=students_map,
    )


@activity_bp.route("/teacher/submission/<int:submission_id>")
@login_required
@role_required("TEACHER")
def teacher_submission_detail(submission_id):
    """View a submission detail (teacher)."""
    submission = get_submission(submission_id)
    if submission is None:
        flash("ارسال یافت نشد.", "error")
        return redirect(url_for("activity.teacher_my_classes"))

    activity = get_activity(submission.activity_id)
    if activity is None or activity.class_id is None:
        abort(404)

    if not is_teacher_of_class(current_user.id, activity.class_id):
        abort(403)

    student = UserModel.query.get(submission.student_user_id)
    files = get_entity_files("activity_submission", submission_id)

    return render_template(
        "activity/teacher_submission.html",
        submission=submission,
        activity=activity,
        student=student,
        files=files,
    )


@activity_bp.route("/teacher/submission/<int:submission_id>/grade", methods=["POST"])
@login_required
@role_required("TEACHER")
def teacher_grade_submission(submission_id):
    """Grade a submission (teacher)."""
    submission = get_submission(submission_id)
    if submission is None:
        flash("ارسال یافت نشد.", "error")
        return redirect(url_for("activity.teacher_my_classes"))

    activity = get_activity(submission.activity_id)
    if activity is None or activity.class_id is None:
        abort(404)

    if not is_teacher_of_class(current_user.id, activity.class_id):
        abort(403)

    try:
        score = float(request.form.get("score", 0))
        feedback = request.form.get("feedback", "")
        grade_submission(submission, score, feedback, graded_by=current_user.id)
        flash("ارسال نمره‌گذاری شد.", "success")
    except (ActivityError, ValueError) as e:
        flash(str(e), "error")

    return redirect(
        url_for("activity.teacher_submission_detail", submission_id=submission_id)
    )


@activity_bp.route("/teacher/submission/<int:submission_id>/return", methods=["POST"])
@login_required
@role_required("TEACHER")
def teacher_return_submission(submission_id):
    """Return a submission for correction (teacher)."""
    submission = get_submission(submission_id)
    if submission is None:
        flash("ارسال یافت نشد.", "error")
        return redirect(url_for("activity.teacher_my_classes"))

    activity = get_activity(submission.activity_id)
    if activity is None or activity.class_id is None:
        abort(404)

    if not is_teacher_of_class(current_user.id, activity.class_id):
        abort(403)

    feedback = request.form.get("feedback", "")
    return_submission(submission, feedback, graded_by=current_user.id)
    flash("ارسال برای اصلاح بازگردانده شد.", "success")

    return redirect(
        url_for("activity.teacher_submission_detail", submission_id=submission_id)
    )


# ---------------------------------------------------------------------------
# Student routes
# ---------------------------------------------------------------------------


@activity_bp.route("/student/my-classes")
@login_required
@role_required("STUDENT")
def student_my_classes():
    """List student's enrolled classes."""
    classes = get_student_enrolled_classes(current_user.id)
    return render_template("activity/student_classes.html", classes=classes)


@activity_bp.route("/student/class/<int:class_id>/activities")
@login_required
@role_required("STUDENT")
def student_class_activities(class_id):
    """List activities for a student's class."""
    if not is_student_enrolled(current_user.id, class_id):
        flash("شما در این کلاس ثبت‌نام نکرده‌اید.", "error")
        return redirect(url_for("activity.student_my_classes"))

    activities = list_activities_by_class(class_id)
    academy_class = AcademyClassModel.query.get(class_id)

    return render_template(
        "activity/student_class_activities.html",
        academy_class=academy_class,
        activities=activities,
    )


@activity_bp.route("/student/<int:activity_id>")
@login_required
@role_required("STUDENT")
def student_activity_detail(activity_id):
    """View activity details and submit."""
    activity = get_activity(activity_id)
    if activity is None:
        flash("فعالیت یافت نشد.", "error")
        return redirect(url_for("activity.student_my_classes"))

    if activity.class_id is None:
        flash("فعالیت یافت نشد.", "error")
        return redirect(url_for("activity.student_my_classes"))

    if not is_student_enrolled(current_user.id, activity.class_id):
        flash("شما در این کلاس ثبت‌نام نکرده‌اید.", "error")
        return redirect(url_for("activity.student_my_classes"))

    from app.application.activity.activity_service import get_latest_submission

    latest = get_latest_submission(activity_id, current_user.id)
    history = get_submission_history(activity_id, current_user.id)
    files = get_entity_files("activity_submission", latest.id) if latest else []

    academy_class = AcademyClassModel.query.get(activity.class_id)

    return render_template(
        "activity/student_detail.html",
        activity=activity,
        academy_class=academy_class,
        latest=latest,
        history=history,
        files=files,
    )


@activity_bp.route("/student/<int:activity_id>/submit", methods=["POST"])
@login_required
@role_required("STUDENT")
def student_submit_activity(activity_id):
    """Submit or resubmit an activity."""
    activity = get_activity(activity_id)
    if activity is None:
        flash("فعالیت یافت نشد.", "error")
        return redirect(url_for("activity.student_my_classes"))

    if activity.class_id is None:
        flash("فعالیت یافت نشد.", "error")
        return redirect(url_for("activity.student_my_classes"))

    if not is_student_enrolled(current_user.id, activity.class_id):
        flash("شما در این کلاس ثبت‌نام نکرده‌اید.", "error")
        return redirect(url_for("activity.student_my_classes"))

    text_content = request.form.get("text_content", "")

    try:
        submission = submit_activity(activity_id, current_user.id, text_content)

        uploaded_files = request.files.getlist("files")
        for f in uploaded_files:
            if f.filename:
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                f.seek(0)
                upload_file(
                    file_storage=f,
                    filename=f.filename,
                    file_size=file_size,
                    content_type=f.content_type,
                    category="ACTIVITY_SUBMISSION",
                    uploader_user_id=current_user.id,
                    entity_type="activity_submission",
                    entity_id=submission.id,
                    allowed_extensions=frozenset(
                        {
                            "pdf",
                            "doc",
                            "docx",
                            "xls",
                            "xlsx",
                            "ppt",
                            "pptx",
                            "jpg",
                            "jpeg",
                            "png",
                            "zip",
                        }
                    ),
                    max_size=5 * 1024 * 1024,
                )

        flash("فعالیت با موفقیت ارسال شد.", "success")
    except (ActivityError, FileError) as e:
        flash(str(e), "error")

    return redirect(
        url_for("activity.student_activity_detail", activity_id=activity_id)
    )


@activity_bp.route("/student/history/<int:activity_id>")
@login_required
@role_required("STUDENT")
def student_submission_history(activity_id):
    """View submission history for an activity."""
    activity = get_activity(activity_id)
    if activity is None:
        flash("فعالیت یافت نشد.", "error")
        return redirect(url_for("activity.student_my_classes"))

    if activity.class_id is None:
        flash("فعالیت یافت نشد.", "error")
        return redirect(url_for("activity.student_my_classes"))

    if not is_student_enrolled(current_user.id, activity.class_id):
        flash("شما در این کلاس ثبت‌نام نکرده‌اید.", "error")
        return redirect(url_for("activity.student_my_classes"))

    history = get_submission_history(activity_id, current_user.id)

    return render_template(
        "activity/student_history.html",
        activity=activity,
        history=history,
    )


# ---------------------------------------------------------------------------
# File download
# ---------------------------------------------------------------------------


@activity_bp.route("/file/<int:file_id>/download")
@login_required
def download_file(file_id):
    """Download an activity file via P11 storage backend."""
    file_record = StoredFileModel.query.get(file_id)
    if file_record is None:
        abort(404)

    if file_record.status == "DELETED":
        abort(404)

    submission = get_submission(file_record.entity_id)
    if submission is None:
        abort(404)

    activity = get_activity(submission.activity_id)
    if activity is None:
        abort(404)

    is_owner = submission.student_user_id == current_user.id
    is_admin = current_user.has_role("ADMIN")
    is_teacher = current_user.has_role("TEACHER") and (
        activity.class_id is not None
        and is_teacher_of_class(current_user.id, activity.class_id)
    )

    if not (is_owner or is_admin or is_teacher):
        abort(403)

    try:
        record, stream = get_file_stream(file_id)
        from flask import send_file

        return send_file(
            stream,
            mimetype=record.mime_type,
            download_name=record.original_filename,
        )
    except FileError:
        abort(404)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_activity_from_form(form, class_id=None):
    """Create an activity from form data."""
    activity_type = form.get("type", "HOMEWORK")
    title = form.get("title", "")
    description = form.get("description", "")
    requirement = form.get("requirement", "REQUIRED")
    max_score = float(form.get("max_score", 100))
    sort_order = int(form.get("sort_order", 0))

    deadline_str = form.get("deadline", "")
    deadline = None
    if deadline_str:
        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%dT%H:%M")
        except ValueError:
            try:
                deadline = datetime.strptime(deadline_str, "%Y-%m-%d")
            except ValueError:
                pass

    course_id = form.get("course_id", type=int)
    session_id = form.get("session_id", type=int)

    effective_class_id = class_id or form.get("class_id", type=int)

    return create_activity(
        activity_type=activity_type,
        title=title,
        description=description,
        requirement=requirement,
        deadline=deadline,
        max_score=max_score,
        course_id=course_id if not effective_class_id else None,
        class_id=effective_class_id,
        session_id=session_id,
        sort_order=sort_order,
    )


def _update_activity_from_form(activity, form):
    """Update an activity from form data."""
    title = form.get("title", "")
    description = form.get("description", "")
    requirement = form.get("requirement", "REQUIRED")
    max_score = float(form.get("max_score", 100))
    sort_order = int(form.get("sort_order", 0))

    deadline_str = form.get("deadline", "")
    deadline = None
    if deadline_str:
        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%dT%H:%M")
        except ValueError:
            try:
                deadline = datetime.strptime(deadline_str, "%Y-%m-%d")
            except ValueError:
                pass

    session_id = form.get("session_id", type=int)

    update_activity(
        activity=activity,
        title=title,
        description=description,
        requirement=requirement,
        deadline=deadline,
        max_score=max_score,
        sort_order=sort_order,
        session_id=session_id,
    )
