from __future__ import annotations

import os
import uuid
from datetime import datetime
from decimal import Decimal

from flask import current_app

from app.extensions import db
from app.infrastructure.database.models import (
    AcademyClassModel,
    ActivityFileModel,
    ActivityModel,
    ActivitySubmissionModel,
    CourseModel,
    EnrollmentModel,
    SessionModel,
)

VALID_ACTIVITY_TYPES = {"HOMEWORK", "PROJECT", "PRACTICE", "QUIZ", "EXAM"}
VALID_REQUIREMENTS = {"REQUIRED", "OPTIONAL"}
VALID_SUBMISSION_STATUSES = {
    "NOT_SUBMITTED",
    "SUBMITTED",
    "LATE",
    "GRADED",
    "RETURNED",
}


class ActivityError(Exception):
    """Raised when an activity operation fails."""


# ---------------------------------------------------------------------------
# Activity CRUD
# ---------------------------------------------------------------------------


def create_activity(
    activity_type: str,
    title: str,
    description: str = "",
    requirement: str = "REQUIRED",
    deadline: datetime | None = None,
    max_score: float = 100.0,
    course_id: int | None = None,
    class_id: int | None = None,
    session_id: int | None = None,
    sort_order: int = 0,
) -> ActivityModel:
    """Create a new learning activity."""
    if activity_type not in VALID_ACTIVITY_TYPES:
        raise ActivityError(f"Invalid activity type: {activity_type}")
    if requirement not in VALID_REQUIREMENTS:
        raise ActivityError(f"Invalid requirement: {requirement}")
    if not title or not title.strip():
        raise ActivityError("Activity title is required.")
    if max_score < 0:
        raise ActivityError("Maximum score must be non-negative.")

    if session_id is not None:
        session = SessionModel.query.get(session_id)
        if session is None:
            raise ActivityError("Session not found.")
        if class_id is None:
            class_id = session.class_id
        elif class_id != session.class_id:
            raise ActivityError("Session does not belong to the specified class.")

    if class_id is not None:
        academy_class = AcademyClassModel.query.get(class_id)
        if academy_class is None:
            raise ActivityError("Class not found.")

    if course_id is not None:
        course = CourseModel.query.get(course_id)
        if course is None:
            raise ActivityError("Course not found.")

    activity = ActivityModel(
        type=activity_type,
        title=title.strip(),
        description=description,
        requirement=requirement,
        deadline=deadline,
        max_score=Decimal(str(max_score)),
        is_active=True,
        sort_order=sort_order,
        course_id=course_id,
        class_id=class_id,
        session_id=session_id,
    )
    db.session.add(activity)
    db.session.commit()
    return activity


def update_activity(
    activity: ActivityModel,
    title: str | None = None,
    description: str | None = None,
    requirement: str | None = None,
    deadline: datetime | None = None,
    max_score: float | None = None,
    sort_order: int | None = None,
    session_id: int | None = None,
) -> ActivityModel:
    """Update an existing activity."""
    if title is not None:
        if not title.strip():
            raise ActivityError("Activity title cannot be empty.")
        activity.title = title.strip()
    if description is not None:
        activity.description = description
    if requirement is not None:
        if requirement not in VALID_REQUIREMENTS:
            raise ActivityError(f"Invalid requirement: {requirement}")
        activity.requirement = requirement
    if deadline is not None:
        activity.deadline = deadline
    if max_score is not None:
        if max_score < 0:
            raise ActivityError("Maximum score must be non-negative.")
        activity.max_score = Decimal(str(max_score))
    if sort_order is not None:
        activity.sort_order = sort_order
    if session_id is not None:
        session = SessionModel.query.get(session_id)
        if session is None:
            raise ActivityError("Session not found.")
        if activity.class_id is not None and session.class_id != activity.class_id:
            raise ActivityError("Session does not belong to the activity's class.")
        activity.session_id = session_id

    db.session.commit()
    return activity


def deactivate_activity(activity: ActivityModel) -> ActivityModel:
    """Soft-disable an activity."""
    activity.is_active = False
    db.session.commit()
    return activity


def get_activity(activity_id: int) -> ActivityModel | None:
    """Get an activity by ID."""
    return ActivityModel.query.get(activity_id)


def list_activities_by_course(course_id: int) -> list[ActivityModel]:
    """List active activities for a course."""
    return (
        ActivityModel.query.filter_by(course_id=course_id, is_active=True)
        .order_by(ActivityModel.sort_order, ActivityModel.id)
        .all()
    )


def list_activities_by_class(class_id: int) -> list[ActivityModel]:
    """List active activities for a class."""
    return (
        ActivityModel.query.filter_by(class_id=class_id, is_active=True)
        .order_by(ActivityModel.sort_order, ActivityModel.id)
        .all()
    )


def list_activities_by_class_all(class_id: int) -> list[ActivityModel]:
    """List all activities (including inactive) for a class."""
    return (
        ActivityModel.query.filter_by(class_id=class_id)
        .order_by(ActivityModel.sort_order, ActivityModel.id)
        .all()
    )


def list_activities_by_session(session_id: int) -> list[ActivityModel]:
    """List active activities for a session."""
    return (
        ActivityModel.query.filter_by(session_id=session_id, is_active=True)
        .order_by(ActivityModel.sort_order, ActivityModel.id)
        .all()
    )


# ---------------------------------------------------------------------------
# Course → Class activity copying
# ---------------------------------------------------------------------------


def copy_course_activities_to_class(
    course_id: int, class_id: int
) -> list[ActivityModel]:
    """Copy course-level default activities into a class.

    Creates new ActivityModel records with class_id set.
    Course defaults are not modified.
    """
    course_activities = (
        ActivityModel.query.filter_by(
            course_id=course_id, class_id=None, is_active=True
        )
        .order_by(ActivityModel.sort_order)
        .all()
    )

    copied = []
    for source in course_activities:
        new_activity = ActivityModel(
            type=source.type,
            title=source.title,
            description=source.description,
            requirement=source.requirement,
            deadline=source.deadline,
            max_score=source.max_score,
            is_active=True,
            sort_order=source.sort_order,
            class_id=class_id,
            session_id=None,
        )
        db.session.add(new_activity)
        copied.append(new_activity)

    if copied:
        db.session.commit()

    return copied


# ---------------------------------------------------------------------------
# Submission management
# ---------------------------------------------------------------------------


def submit_activity(
    activity_id: int,
    student_user_id: int,
    text_content: str = "",
) -> ActivitySubmissionModel:
    """Submit or resubmit an activity.

    Each call creates a new versioned submission record.
    """
    activity = ActivityModel.query.get(activity_id)
    if activity is None:
        raise ActivityError("Activity not found.")

    if not activity.is_active:
        raise ActivityError("This activity is no longer active.")

    enrollment = _get_approved_enrollment(student_user_id, activity.class_id)
    if enrollment is None:
        raise ActivityError("Student is not enrolled in the class for this activity.")

    latest = _get_latest_submission(activity_id, student_user_id)
    version = (latest.version + 1) if latest else 1

    now = datetime.now()
    is_late = activity.deadline is not None and now > activity.deadline
    status = "LATE" if is_late else "SUBMITTED"

    submission = ActivitySubmissionModel(
        activity_id=activity_id,
        student_user_id=student_user_id,
        enrollment_id=enrollment.id,
        text_content=text_content,
        submitted_at=now,
        status=status,
        version=version,
    )
    db.session.add(submission)
    db.session.commit()
    return submission


def get_submission(submission_id: int) -> ActivitySubmissionModel | None:
    """Get a submission by ID."""
    return ActivitySubmissionModel.query.get(submission_id)


def get_latest_submission(
    activity_id: int, student_user_id: int
) -> ActivitySubmissionModel | None:
    """Get the latest submission for an activity by a student."""
    return _get_latest_submission(activity_id, student_user_id)


def get_submission_history(
    activity_id: int, student_user_id: int
) -> list[ActivitySubmissionModel]:
    """Get all submission versions for an activity by a student."""
    return (
        ActivitySubmissionModel.query.filter_by(
            activity_id=activity_id,
            student_user_id=student_user_id,
        )
        .order_by(ActivitySubmissionModel.version)
        .all()
    )


def get_all_submissions_for_activity(
    activity_id: int,
) -> list[ActivitySubmissionModel]:
    """Get the latest submission per student for an activity (teacher view)."""
    subq = (
        db.session.query(
            ActivitySubmissionModel.student_user_id,
            db.func.max(ActivitySubmissionModel.version).label("max_version"),
        )
        .filter_by(activity_id=activity_id)
        .group_by(ActivitySubmissionModel.student_user_id)
        .subquery()
    )

    results = (
        db.session.query(ActivitySubmissionModel)
        .join(
            subq,
            db.and_(
                ActivitySubmissionModel.activity_id == activity_id,
                ActivitySubmissionModel.student_user_id == subq.c.student_user_id,
                ActivitySubmissionModel.version == subq.c.max_version,
            ),
        )
        .order_by(ActivitySubmissionModel.student_user_id)
        .all()
    )
    return results


def get_student_class_submissions(
    student_user_id: int, class_id: int
) -> list[ActivitySubmissionModel]:
    """Get latest submissions for a student in a class."""
    activities = list_activities_by_class(class_id)
    activity_ids = [a.id for a in activities]
    if not activity_ids:
        return []

    subq = (
        db.session.query(
            ActivitySubmissionModel.activity_id,
            db.func.max(ActivitySubmissionModel.version).label("max_version"),
        )
        .filter(
            ActivitySubmissionModel.activity_id.in_(activity_ids),
            ActivitySubmissionModel.student_user_id == student_user_id,
        )
        .group_by(ActivitySubmissionModel.activity_id)
        .subquery()
    )

    return (
        db.session.query(ActivitySubmissionModel)
        .join(
            subq,
            db.and_(
                ActivitySubmissionModel.activity_id == subq.c.activity_id,
                ActivitySubmissionModel.version == subq.c.max_version,
            ),
        )
        .order_by(ActivitySubmissionModel.activity_id)
        .all()
    )


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------


def grade_submission(
    submission: ActivitySubmissionModel,
    score: float,
    feedback: str = "",
    graded_by: int | None = None,
) -> ActivitySubmissionModel:
    """Grade a submission."""
    if score < 0:
        raise ActivityError("Score cannot be negative.")

    activity = ActivityModel.query.get(submission.activity_id)
    if activity is None:
        raise ActivityError("Activity not found.")

    if Decimal(str(score)) > activity.max_score:
        raise ActivityError(
            f"Score cannot exceed maximum score of {activity.max_score}."
        )

    now = datetime.now()
    submission.score = Decimal(str(score))
    submission.feedback = feedback
    submission.graded_at = now
    submission.graded_by = graded_by
    submission.status = "GRADED"
    db.session.commit()
    return submission


def return_submission(
    submission: ActivitySubmissionModel,
    feedback: str,
    graded_by: int | None = None,
) -> ActivitySubmissionModel:
    """Return a submission for correction/resubmission."""
    submission.feedback = feedback
    submission.graded_by = graded_by
    submission.graded_at = datetime.now()
    submission.status = "RETURNED"
    db.session.commit()
    return submission


# ---------------------------------------------------------------------------
# File management
# ---------------------------------------------------------------------------


def validate_file(filename: str, file_size: int, content_type: str | None) -> None:
    """Validate an uploaded file against size and type constraints."""
    from app.infrastructure.database.models import (
        ALLOWED_ACTIVITY_EXTENSIONS,
        ALLOWED_ACTIVITY_MIMETYPES,
        MAX_FILE_SIZE_BYTES,
    )

    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if ext not in ALLOWED_ACTIVITY_EXTENSIONS:
        raise ActivityError(
            f"File type '.{ext}' is not allowed. "
            f"Allowed types: {', '.join(sorted(ALLOWED_ACTIVITY_EXTENSIONS))}"
        )

    if file_size > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise ActivityError(f"File size exceeds maximum of {max_mb} MB.")

    if content_type and content_type not in ALLOWED_ACTIVITY_MIMETYPES:
        raise ActivityError(f"File type '{content_type}' is not allowed.")


def save_file_upload(
    submission: ActivitySubmissionModel,
    file_storage,
    filename: str,
    file_size: int,
    content_type: str | None = None,
) -> ActivityFileModel:
    """Validate and save an uploaded file, creating an ActivityFileModel record."""
    validate_file(filename, file_size, content_type)

    ext = os.path.splitext(filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"

    upload_dir = os.path.join(
        current_app.config.get("UPLOAD_FOLDER", "uploads"),
        "activity_submissions",
        str(submission.id),
    )
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, unique_name)
    file_storage.save(file_path)

    record = ActivityFileModel(
        submission_id=submission.id,
        filename=unique_name,
        original_filename=filename,
        file_size=file_size,
        mime_type=content_type or "application/octet-stream",
    )
    db.session.add(record)
    db.session.commit()
    return record


def get_submission_files(submission_id: int) -> list[ActivityFileModel]:
    """Get all files for a submission."""
    return (
        ActivityFileModel.query.filter_by(submission_id=submission_id)
        .order_by(ActivityFileModel.id)
        .all()
    )


# ---------------------------------------------------------------------------
# Authorization helpers
# ---------------------------------------------------------------------------


def is_teacher_of_class(teacher_user_id: int, class_id: int) -> bool:
    """Check if a teacher is assigned to a class."""
    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        return False
    return academy_class.teacher_user_id == teacher_user_id


def is_student_enrolled(student_user_id: int, class_id: int) -> bool:
    """Check if a student has an approved enrollment in a class."""
    return _get_approved_enrollment(student_user_id, class_id) is not None


def get_student_enrolled_classes(student_user_id: int) -> list[AcademyClassModel]:
    """Get all classes a student is enrolled in (approved)."""
    enrollments = EnrollmentModel.query.filter_by(
        student_user_id=student_user_id, status="APPROVED"
    ).all()
    class_ids = [e.class_id for e in enrollments]
    if not class_ids:
        return []
    return (
        AcademyClassModel.query.filter(AcademyClassModel.id.in_(class_ids))
        .order_by(AcademyClassModel.title)
        .all()
    )


def get_class_enrolled_students(class_id: int) -> list[EnrollmentModel]:
    """Get all approved enrollments for a class."""
    return (
        EnrollmentModel.query.filter_by(class_id=class_id, status="APPROVED")
        .order_by(EnrollmentModel.id)
        .all()
    )


def compute_activity_submissions_summary(activity_id: int) -> dict:
    """Compute submission summary for an activity.

    Returns counts of submitted, late, graded, not submitted.
    """
    activity = ActivityModel.query.get(activity_id)
    if activity is None:
        raise ActivityError("Activity not found.")

    if activity.class_id is None:
        return {"total": 0, "submitted": 0, "late": 0, "graded": 0, "not_submitted": 0}

    enrollments = get_class_enrolled_students(activity.class_id)
    total = len(enrollments)

    latest_submissions = get_all_submissions_for_activity(activity_id)
    submission_map = {s.student_user_id: s for s in latest_submissions}

    submitted = 0
    late = 0
    graded = 0
    not_submitted = 0

    for enrollment in enrollments:
        sub = submission_map.get(enrollment.student_user_id)
        if sub is None or sub.status == "NOT_SUBMITTED":
            not_submitted += 1
        else:
            submitted += 1
            if sub.status == "LATE":
                late += 1
            if sub.status == "GRADED":
                graded += 1

    return {
        "total": total,
        "submitted": submitted,
        "late": late,
        "graded": graded,
        "not_submitted": not_submitted,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_approved_enrollment(
    student_user_id: int, class_id: int | None
) -> EnrollmentModel | None:
    """Get the approved enrollment for a student in a class."""
    if class_id is None:
        return None
    return EnrollmentModel.query.filter_by(
        student_user_id=student_user_id,
        class_id=class_id,
        status="APPROVED",
    ).first()


def _get_latest_submission(
    activity_id: int, student_user_id: int
) -> ActivitySubmissionModel | None:
    """Get the latest submission version for an activity by a student."""
    return (
        ActivitySubmissionModel.query.filter_by(
            activity_id=activity_id,
            student_user_id=student_user_id,
        )
        .order_by(ActivitySubmissionModel.version.desc())
        .first()
    )
