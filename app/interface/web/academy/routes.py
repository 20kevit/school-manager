from datetime import time

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.application.academic_calendar.service import list_semesters
from app.application.academy.class_service import (
    ClassError,
    cancel_session,
    complete_session,
    create_class,
    get_class,
    get_session,
    get_sessions,
    list_classes,
    reschedule_session,
    shift_sessions_after_cancellation,
    update_class,
    update_class_schedule,
    update_session,
)
from app.application.academy.course_service import (
    CourseError,
    add_syllabus_item,
    create_course,
    delete_course,
    delete_syllabus_item,
    get_course,
    get_next_syllabus_order,
    get_syllabus_items,
    list_courses,
    update_course,
    update_syllabus_item,
)
from app.interface.web.decorators import role_required

academy_bp = Blueprint("academy", __name__, url_prefix="/academy")


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------


@academy_bp.route("/courses")
@login_required
@role_required("ADMIN")
def course_list():
    courses = list_courses()
    return render_template("academy/course_list.html", courses=courses)


@academy_bp.route("/courses/create", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def course_create():
    if request.method == "POST":
        try:
            course = create_course(
                title=request.form["title"],
                description=request.form.get("description", ""),
                num_sessions=int(request.form.get("num_sessions", 1)),
                min_age=_parse_int(request.form.get("min_age")),
                max_age=_parse_int(request.form.get("max_age")),
                prerequisites=request.form.get("prerequisites", ""),
            )
            flash("Course created successfully.", "success")
            return redirect(url_for("academy.course_detail", course_id=course.id))
        except CourseError as e:
            flash(str(e), "error")
    return render_template("academy/course_form.html", course=None)


@academy_bp.route("/courses/<int:course_id>")
@login_required
@role_required("ADMIN")
def course_detail(course_id):
    course = get_course(course_id)
    if course is None:
        flash("Course not found.", "error")
        return redirect(url_for("academy.course_list"))
    syllabus = get_syllabus_items(course_id)
    next_order = get_next_syllabus_order(course_id)
    return render_template(
        "academy/course_detail.html",
        course=course,
        syllabus=syllabus,
        next_order=next_order,
    )


@academy_bp.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def course_edit(course_id):
    course = get_course(course_id)
    if course is None:
        flash("Course not found.", "error")
        return redirect(url_for("academy.course_list"))
    if request.method == "POST":
        try:
            update_course(
                course,
                title=request.form["title"],
                description=request.form.get("description", ""),
                num_sessions=int(request.form.get("num_sessions", 1)),
                min_age=_parse_int(request.form.get("min_age")),
                max_age=_parse_int(request.form.get("max_age")),
                prerequisites=request.form.get("prerequisites", ""),
            )
            flash("Course updated successfully.", "success")
            return redirect(url_for("academy.course_detail", course_id=course.id))
        except CourseError as e:
            flash(str(e), "error")
    return render_template("academy/course_form.html", course=course)


@academy_bp.route("/courses/<int:course_id>/delete", methods=["POST"])
@login_required
@role_required("ADMIN")
def course_delete(course_id):
    course = get_course(course_id)
    if course is None:
        flash("Course not found.", "error")
        return redirect(url_for("academy.course_list"))
    delete_course(course)
    flash("Course deleted.", "success")
    return redirect(url_for("academy.course_list"))


# ---------------------------------------------------------------------------
# Syllabus
# ---------------------------------------------------------------------------


@academy_bp.route("/courses/<int:course_id>/syllabus/add", methods=["POST"])
@login_required
@role_required("ADMIN")
def syllabus_add(course_id):
    course = get_course(course_id)
    if course is None:
        flash("Course not found.", "error")
        return redirect(url_for("academy.course_list"))
    try:
        add_syllabus_item(
            course,
            order=int(request.form["order"]),
            title=request.form["title"],
            description=request.form.get("description", ""),
            homework=request.form.get("homework", ""),
            assessment=request.form.get("assessment", ""),
        )
        flash("Syllabus item added.", "success")
    except CourseError as e:
        flash(str(e), "error")
    return redirect(url_for("academy.course_detail", course_id=course_id))


@academy_bp.route("/syllabus/<int:item_id>/edit", methods=["POST"])
@login_required
@role_required("ADMIN")
def syllabus_edit(item_id):
    from app.infrastructure.database.models import SyllabusItemModel

    item = SyllabusItemModel.query.get(item_id)
    if item is None:
        flash("Syllabus item not found.", "error")
        return redirect(url_for("academy.course_list"))
    try:
        update_syllabus_item(
            item,
            order=int(request.form["order"]),
            title=request.form["title"],
            description=request.form.get("description", ""),
            homework=request.form.get("homework", ""),
            assessment=request.form.get("assessment", ""),
        )
        flash("Syllabus item updated.", "success")
    except CourseError as e:
        flash(str(e), "error")
    return redirect(url_for("academy.course_detail", course_id=item.course_id))


@academy_bp.route("/syllabus/<int:item_id>/delete", methods=["POST"])
@login_required
@role_required("ADMIN")
def syllabus_delete(item_id):
    from app.infrastructure.database.models import SyllabusItemModel

    item = SyllabusItemModel.query.get(item_id)
    if item is None:
        flash("Syllabus item not found.", "error")
        return redirect(url_for("academy.course_list"))
    course_id = item.course_id
    delete_syllabus_item(item)
    flash("Syllabus item deleted.", "success")
    return redirect(url_for("academy.course_detail", course_id=course_id))


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------


@academy_bp.route("/classes")
@login_required
@role_required("ADMIN")
def class_list():
    course_id = request.args.get("course_id", type=int)
    semester_id = request.args.get("semester_id", type=int)
    classes = list_classes(course_id=course_id, semester_id=semester_id)
    courses = list_courses()
    semesters = list_semesters()
    return render_template(
        "academy/class_list.html",
        classes=classes,
        courses=courses,
        semesters=semesters,
        selected_course_id=course_id,
        selected_semester_id=semester_id,
    )


@academy_bp.route("/classes/create", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def class_create():
    from app.infrastructure.database.models import UserModel

    courses = list_courses()
    teachers = UserModel.query.filter(UserModel.roles.any(name="TEACHER")).all()

    if request.method == "POST":
        try:
            schedule = _parse_schedule(request.form)
            teacher_id = _parse_int(request.form.get("teacher_user_id"))
            session_contents = _parse_session_contents(request.form)
            semester_id = _parse_int(request.form.get("semester_id"))

            academy_class = create_class(
                course_id=int(request.form["course_id"]),
                title=request.form["title"],
                start_date=_parse_date(request.form["start_date"]),
                capacity=int(request.form.get("capacity", 30)),
                num_sessions=_parse_int(request.form.get("num_sessions")),
                end_date=_parse_date_optional(request.form.get("end_date")),
                teacher_user_id=teacher_id,
                semester_id=semester_id,
                schedule=schedule,
                session_contents=session_contents if session_contents else None,
            )
            flash("کلاس با موفقیت ایجاد شد.", "success")
            return redirect(url_for("academy.class_detail", class_id=academy_class.id))
        except (ClassError, ValueError, KeyError) as e:
            flash(str(e), "error")

    return render_template(
        "academy/class_form.html",
        class_obj=None,
        courses=courses,
        teachers=teachers,
        semesters=list_semesters(),
    )


@academy_bp.route("/classes/<int:class_id>")
@login_required
@role_required("ADMIN")
def class_detail(class_id):
    academy_class = get_class(class_id)
    if academy_class is None:
        flash("Class not found.", "error")
        return redirect(url_for("academy.class_list"))
    sessions = get_sessions(class_id)
    schedule = academy_class.schedule_entries
    return render_template(
        "academy/class_detail.html",
        class_obj=academy_class,
        sessions=sessions,
        schedule=schedule,
    )


@academy_bp.route("/classes/<int:class_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def class_edit(class_id):
    academy_class = get_class(class_id)
    if academy_class is None:
        flash("Class not found.", "error")
        return redirect(url_for("academy.class_list"))

    courses = list_courses()
    teachers = []  # Could fetch teachers here if needed

    if request.method == "POST":
        try:
            update_class(
                academy_class,
                title=request.form["title"],
                capacity=int(request.form.get("capacity", 30)),
                teacher_user_id=_parse_int(request.form.get("teacher_user_id")),
                status=request.form.get("status", academy_class.status),
            )
            flash("Class updated successfully.", "success")
            return redirect(url_for("academy.class_detail", class_id=class_id))
        except ClassError as e:
            flash(str(e), "error")
    return render_template(
        "academy/class_form.html",
        class_obj=academy_class,
        courses=courses,
        teachers=teachers,
    )


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------


@academy_bp.route("/classes/<int:class_id>/schedule", methods=["POST"])
@login_required
@role_required("ADMIN")
def schedule_update(class_id):
    academy_class = get_class(class_id)
    if academy_class is None:
        flash("Class not found.", "error")
        return redirect(url_for("academy.class_list"))
    try:
        schedule = _parse_schedule(request.form)
        update_class_schedule(academy_class, schedule)
        flash("Schedule updated.", "success")
    except (ClassError, ValueError) as e:
        flash(str(e), "error")
    return redirect(url_for("academy.class_detail", class_id=class_id))


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@academy_bp.route("/classes/<int:class_id>/sessions")
@login_required
@role_required("ADMIN")
def session_list(class_id):
    academy_class = get_class(class_id)
    if academy_class is None:
        flash("Class not found.", "error")
        return redirect(url_for("academy.class_list"))
    sessions = get_sessions(class_id)
    return render_template(
        "academy/session_list.html",
        class_obj=academy_class,
        sessions=sessions,
    )


@academy_bp.route("/sessions/<int:session_id>")
@login_required
@role_required("ADMIN")
def session_detail(session_id):
    session = get_session(session_id)
    if session is None:
        flash("Session not found.", "error")
        return redirect(url_for("academy.class_list"))
    academy_class = get_class(session.class_id)
    return render_template(
        "academy/session_detail.html",
        session=session,
        class_obj=academy_class,
    )


@academy_bp.route("/sessions/<int:session_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def session_edit(session_id):
    session = get_session(session_id)
    if session is None:
        flash("Session not found.", "error")
        return redirect(url_for("academy.class_list"))
    academy_class = get_class(session.class_id)
    if request.method == "POST":
        try:
            update_session(
                session,
                title=request.form.get("title"),
                description=request.form.get("description"),
                scheduled_date=_parse_date(request.form["scheduled_date"]),
                start_time=_parse_time(request.form["start_time"]),
                end_time=_parse_time(request.form["end_time"]),
                edited_by=current_user.id,
            )
            flash("Session updated successfully.", "success")
            return redirect(url_for("academy.session_detail", session_id=session_id))
        except (ClassError, ValueError) as e:
            flash(str(e), "error")
    return render_template(
        "academy/session_edit.html",
        session=session,
        class_obj=academy_class,
    )


@academy_bp.route("/sessions/<int:session_id>/reschedule", methods=["POST"])
@login_required
@role_required("ADMIN")
def session_reschedule(session_id):
    session = get_session(session_id)
    if session is None:
        flash("Session not found.", "error")
        return redirect(url_for("academy.class_list"))
    try:
        reschedule_session(
            session,
            new_date=_parse_date(request.form["new_date"]),
            new_start_time=_parse_time(request.form["new_start_time"]),
            new_end_time=_parse_time(request.form["new_end_time"]),
        )
        flash("Session rescheduled.", "success")
    except (ClassError, ValueError) as e:
        flash(str(e), "error")
    return redirect(url_for("academy.session_detail", session_id=session_id))


@academy_bp.route("/sessions/<int:session_id>/cancel", methods=["POST"])
@login_required
@role_required("ADMIN")
def session_cancel(session_id):
    session = get_session(session_id)
    if session is None:
        flash("Session not found.", "error")
        return redirect(url_for("academy.class_list"))
    cancel_session(session)
    flash("Session cancelled.", "success")
    return redirect(url_for("academy.session_detail", session_id=session_id))


@academy_bp.route("/sessions/<int:session_id>/complete", methods=["POST"])
@login_required
@role_required("ADMIN")
def session_complete(session_id):
    session = get_session(session_id)
    if session is None:
        flash("Session not found.", "error")
        return redirect(url_for("academy.class_list"))
    complete_session(session)
    flash("Session marked as completed.", "success")
    return redirect(url_for("academy.session_detail", session_id=session_id))


@academy_bp.route(
    "/classes/<int:class_id>/sessions/<int:session_number>/shift", methods=["POST"]
)
@login_required
@role_required("ADMIN")
def session_shift(class_id, session_number):
    academy_class = get_class(class_id)
    if academy_class is None:
        flash("Class not found.", "error")
        return redirect(url_for("academy.class_list"))
    try:
        shift_sessions_after_cancellation(academy_class, session_number)
        flash("Sessions shifted.", "success")
    except ClassError as e:
        flash(str(e), "error")
    return redirect(url_for("academy.session_list", class_id=class_id))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_int(value: str | None) -> int | None:
    if not value or not value.strip():
        return None
    return int(value)


def _parse_date(value: str):
    from app.utils.date_utils import parse_jalali_date

    return parse_jalali_date(value)


def _parse_date_optional(value: str | None):
    from app.utils.date_utils import parse_jalali_date_or_none

    return parse_jalali_date_or_none(value)


def _parse_time(value: str) -> time:
    parts = value.split(":")
    return time(int(parts[0]), int(parts[1]))


def _parse_schedule(form) -> list[dict]:
    """Parse schedule entries from form data.

    Expects form fields like schedule_weekday_0, schedule_start_0, schedule_end_0.
    """
    schedule = []
    i = 0
    while True:
        weekday = form.get(f"schedule_weekday_{i}")
        if weekday is None:
            break
        start_str = form.get(f"schedule_start_{i}", "")
        end_str = form.get(f"schedule_end_{i}", "")
        if weekday and start_str and end_str:
            schedule.append(
                {
                    "weekday": weekday,
                    "start_time": _parse_time(start_str),
                    "end_time": _parse_time(end_str),
                }
            )
        i += 1
    return schedule


def _parse_session_contents(form) -> list[dict]:
    """Parse session content overrides from form data."""
    contents = []
    i = 0
    while True:
        num = form.get(f"content_session_{i}")
        if num is None:
            break
        title = form.get(f"content_title_{i}", "")
        if num and title:
            contents.append(
                {
                    "session_number": int(num),
                    "title": title,
                    "description": form.get(f"content_description_{i}", ""),
                    "homework": form.get(f"content_homework_{i}", ""),
                    "assessment": form.get(f"content_assessment_{i}", ""),
                }
            )
        i += 1
    return contents
