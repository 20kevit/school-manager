from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app.extensions import db
from app.infrastructure.database.models import (
    AcademyClassModel,
    AssessmentModel,
    AssessmentResultModel,
    CourseModel,
    EnrollmentModel,
    GradeHistoryModel,
    GradingComponentModel,
    GradingTemplateModel,
    ParentProfileModel,
    StudentProfileModel,
    UserModel,
)

VALID_ASSESSMENT_TYPES = {
    "FINAL_EXAM",
    "MIDTERM",
    "QUIZ",
    "PROJECT",
    "PRACTICAL",
    "ORAL",
    "OTHER",
}
VALID_ASSESSMENT_STATUSES = {
    "DRAFT",
    "SCHEDULED",
    "OPEN",
    "CLOSED",
    "GRADED",
    "CANCELLED",
}
VALID_RESULT_STATUSES = {"NOT_GRADED", "GRADED", "CORRECTED"}
VALID_PRESENCE_STATUSES = {"PRESENT", "ABSENT", "EXCUSED"}
VALID_PASS_FAIL = {"PASS", "FAIL", "NOT_DETERMINED"}


class AssessmentError(Exception):
    """Raised when an assessment operation fails."""


# ---------------------------------------------------------------------------
# Assessment CRUD
# ---------------------------------------------------------------------------


def create_assessment(
    class_id: int,
    assessment_type: str,
    title: str,
    *,
    description: str = "",
    scheduled_date: date | None = None,
    scheduled_time: datetime | None = None,
    duration_minutes: int | None = None,
    max_score: float = 100.0,
    passing_score: float = 60.0,
    penalty_factor: float = 0.0,
    status: str = "DRAFT",
    created_by: int | None = None,
    notes: str = "",
) -> AssessmentModel:
    """Create a new assessment for a class."""
    if assessment_type not in VALID_ASSESSMENT_TYPES:
        raise AssessmentError(f"Invalid assessment type: {assessment_type}")
    if status not in VALID_ASSESSMENT_STATUSES:
        raise AssessmentError(f"Invalid assessment status: {status}")
    if not title or not title.strip():
        raise AssessmentError("Assessment title is required.")
    if max_score <= 0:
        raise AssessmentError("Maximum score must be positive.")
    if passing_score < 0:
        raise AssessmentError("Passing score cannot be negative.")
    if passing_score > max_score:
        raise AssessmentError("Passing score cannot exceed maximum score.")
    if duration_minutes is not None and duration_minutes <= 0:
        raise AssessmentError("Duration must be positive.")
    if penalty_factor < 0 or penalty_factor > 1:
        raise AssessmentError("Penalty factor must be between 0 and 1.")

    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        raise AssessmentError("Class not found.")

    assessment = AssessmentModel(
        class_id=class_id,
        type=assessment_type,
        title=title.strip(),
        description=description,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        duration_minutes=duration_minutes,
        max_score=Decimal(str(max_score)),
        passing_score=Decimal(str(passing_score)),
        penalty_factor=Decimal(str(penalty_factor)),
        status=status,
        created_by=created_by,
        notes=notes,
    )
    db.session.add(assessment)
    db.session.commit()
    return assessment


def update_assessment(
    assessment: AssessmentModel,
    *,
    title: str | None = None,
    description: str | None = None,
    scheduled_date: date | None = None,
    scheduled_time: datetime | None = None,
    duration_minutes: int | None = None,
    max_score: float | None = None,
    passing_score: float | None = None,
    notes: str | None = None,
) -> AssessmentModel:
    """Update an existing assessment (only DRAFT assessments can be fully edited)."""
    if title is not None:
        if not title.strip():
            raise AssessmentError("Assessment title cannot be empty.")
        assessment.title = title.strip()
    if description is not None:
        assessment.description = description
    if scheduled_date is not None:
        assessment.scheduled_date = scheduled_date
    if scheduled_time is not None:
        assessment.scheduled_time = scheduled_time
    if duration_minutes is not None:
        if duration_minutes <= 0:
            raise AssessmentError("Duration must be positive.")
        assessment.duration_minutes = duration_minutes
    if max_score is not None:
        if max_score <= 0:
            raise AssessmentError("Maximum score must be positive.")
        assessment.max_score = Decimal(str(max_score))
        # Ensure passing_score doesn't exceed new max
        if assessment.passing_score > assessment.max_score:
            assessment.passing_score = assessment.max_score
    if passing_score is not None:
        if passing_score < 0:
            raise AssessmentError("Passing score cannot be negative.")
        if passing_score > assessment.max_score:
            raise AssessmentError("Passing score cannot exceed maximum score.")
        assessment.passing_score = Decimal(str(passing_score))
    if notes is not None:
        assessment.notes = notes

    db.session.commit()
    return assessment


def update_assessment_status(
    assessment: AssessmentModel, new_status: str
) -> AssessmentModel:
    """Update assessment status with lifecycle validation."""
    if new_status not in VALID_ASSESSMENT_STATUSES:
        raise AssessmentError(f"Invalid assessment status: {new_status}")

    if not assessment.can_transition_to(new_status):
        raise AssessmentError(
            f"Cannot transition from {assessment.status} to {new_status}."
        )

    assessment.status = new_status
    db.session.commit()
    return assessment


def cancel_assessment(assessment: AssessmentModel) -> AssessmentModel:
    """Cancel an assessment. Results are preserved."""
    if assessment.status == "CANCELLED":
        raise AssessmentError("Assessment is already cancelled.")
    assessment.status = "CANCELLED"
    db.session.commit()
    return assessment


def reschedule_assessment(
    assessment: AssessmentModel,
    new_date: date,
    new_time: datetime | None = None,
) -> AssessmentModel:
    """Reschedule an assessment to a new date/time."""
    if assessment.status == "CANCELLED":
        raise AssessmentError("Cannot reschedule a cancelled assessment.")
    if assessment.status == "GRADED":
        raise AssessmentError("Cannot reschedule a graded assessment.")
    assessment.scheduled_date = new_date
    if new_time is not None:
        assessment.scheduled_time = new_time
    assessment.status = "SCHEDULED"
    db.session.commit()
    return assessment


def get_assessment(assessment_id: int) -> AssessmentModel | None:
    """Get an assessment by ID."""
    return AssessmentModel.query.get(assessment_id)


def list_class_assessments(
    class_id: int, include_cancelled: bool = False
) -> list[AssessmentModel]:
    """List assessments for a class."""
    query = AssessmentModel.query.filter_by(class_id=class_id)
    if not include_cancelled:
        query = query.filter(AssessmentModel.status != "CANCELLED")
    return query.order_by(
        AssessmentModel.scheduled_date.desc(), AssessmentModel.id.desc()
    ).all()


def list_all_assessments(
    *,
    class_id: int | None = None,
    assessment_type: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AssessmentModel]:
    """List assessments with optional filters (admin)."""
    query = AssessmentModel.query

    if class_id is not None:
        query = query.filter_by(class_id=class_id)
    if assessment_type is not None:
        query = query.filter_by(type=assessment_type)
    if status is not None:
        query = query.filter_by(status=status)

    return (
        query.order_by(AssessmentModel.scheduled_date.desc(), AssessmentModel.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------


def get_eligible_enrollments(assessment_id: int) -> list[EnrollmentModel]:
    """Get all approved enrollments eligible for an assessment."""
    assessment = AssessmentModel.query.get(assessment_id)
    if assessment is None:
        raise AssessmentError("Assessment not found.")

    return (
        EnrollmentModel.query.filter_by(
            class_id=assessment.class_id,
            status="APPROVED",
        )
        .order_by(EnrollmentModel.id)
        .all()
    )


# ---------------------------------------------------------------------------
# Assessment Results
# ---------------------------------------------------------------------------


def record_result(
    assessment_id: int,
    enrollment_id: int,
    *,
    score: float | None = None,
    wrong_count: int | None = None,
    presence_status: str = "PRESENT",
    comments: str = "",
    graded_by: int | None = None,
) -> AssessmentResultModel:
    """Record or update a result for one student in one assessment.

    If a result already exists for this assessment+enrollment, it is updated.

    For negative marking: if assessment.penalty_factor > 0, the teacher
    inputs the raw correct count as score and wrong_count. The effective
    score is calculated as: score - (wrong_count * penalty_factor), min 0.
    """
    assessment = AssessmentModel.query.get(assessment_id)
    if assessment is None:
        raise AssessmentError("Assessment not found.")

    enrollment = EnrollmentModel.query.get(enrollment_id)
    if enrollment is None:
        raise AssessmentError("Enrollment not found.")

    if enrollment.class_id != assessment.class_id:
        raise AssessmentError("Enrollment does not belong to the assessment's class.")

    if enrollment.status != "APPROVED":
        raise AssessmentError("Results can only be recorded for approved enrollments.")

    if presence_status not in VALID_PRESENCE_STATUSES:
        raise AssessmentError(f"Invalid presence status: {presence_status}")

    max_score = float(assessment.max_score)
    passing_score = float(assessment.passing_score)
    penalty_factor = float(assessment.penalty_factor)

    # Validate score
    if presence_status == "ABSENT":
        score = None
        wrong_count = None
    elif score is not None:
        if score < 0:
            raise AssessmentError("Score cannot be negative.")
        if score > max_score:
            raise AssessmentError(f"Score cannot exceed maximum score of {max_score}.")
        if wrong_count is not None and wrong_count < 0:
            raise AssessmentError("Wrong count cannot be negative.")

    # Apply negative marking if penalty_factor > 0
    effective_score = score
    if (
        score is not None
        and penalty_factor > 0
        and wrong_count is not None
        and wrong_count > 0
    ):
        effective_score = max(0.0, score - (wrong_count * penalty_factor))
        if effective_score > max_score:
            effective_score = max_score

    # Calculate percentage and pass/fail
    percentage = None
    pass_fail = "NOT_DETERMINED"
    if effective_score is not None and presence_status != "ABSENT":
        percentage = round(effective_score / max_score * 100, 2)
        pass_fail = "PASS" if effective_score >= passing_score else "FAIL"

    now = datetime.now()

    existing = AssessmentResultModel.query.filter_by(
        assessment_id=assessment_id,
        enrollment_id=enrollment_id,
    ).first()

    if existing is not None:
        # Record grade history before updating
        if existing.result_status == "GRADED" and effective_score is not None:
            _create_grade_history(
                result=existing,
                new_score=effective_score,
                new_pass_fail=pass_fail,
                corrected_by=graded_by,
                reason="Grade updated",
            )

        # Capture old state for audit logging
        old_values = {
            "score": float(existing.score) if existing.score is not None else None,
            "wrong_count": existing.wrong_count,
            "percentage": float(existing.percentage)
            if existing.percentage is not None
            else None,
            "result_status": existing.result_status,
            "presence_status": existing.presence_status,
            "pass_fail": existing.pass_fail,
            "comments": existing.comments,
        }

        existing.score = (
            Decimal(str(effective_score)) if effective_score is not None else None
        )
        existing.wrong_count = wrong_count
        existing.max_score = Decimal(str(max_score))
        existing.percentage = (
            Decimal(str(percentage)) if percentage is not None else None
        )
        existing.presence_status = presence_status
        existing.pass_fail = pass_fail
        existing.result_status = (
            "GRADED" if effective_score is not None else "NOT_GRADED"
        )
        if comments:
            existing.comments = comments
        if graded_by is not None:
            existing.graded_by = graded_by
            existing.graded_at = now
        existing.updated_at = now
        db.session.commit()

        # Audit log for grade correction
        if graded_by is not None and existing.result_status == "GRADED":
            new_values = {
                "score": float(effective_score)
                if effective_score is not None
                else None,
                "wrong_count": wrong_count,
                "percentage": round(percentage, 2) if percentage is not None else None,
                "result_status": existing.result_status,
                "presence_status": presence_status,
                "pass_fail": pass_fail,
                "comments": comments or existing.comments,
            }
            from app.application.audit.audit_service import log as audit_log

            audit_log(
                user_id=graded_by,
                action="UPDATE",
                entity_type="ASSESSMENT_RESULT",
                entity_id=existing.id,
                old_values=old_values,
                new_values=new_values,
            )

        return existing

    result = AssessmentResultModel(
        assessment_id=assessment_id,
        enrollment_id=enrollment_id,
        student_user_id=enrollment.student_user_id,
        score=Decimal(str(effective_score)) if effective_score is not None else None,
        wrong_count=wrong_count,
        max_score=Decimal(str(max_score)),
        percentage=Decimal(str(percentage)) if percentage is not None else None,
        result_status="GRADED" if effective_score is not None else "NOT_GRADED",
        presence_status=presence_status,
        pass_fail=pass_fail,
        comments=comments,
        graded_by=graded_by,
        graded_at=now if effective_score is not None else None,
    )
    db.session.add(result)
    db.session.commit()
    return result


def record_bulk_results(
    assessment_id: int,
    results_data: list[dict],
    graded_by: int | None = None,
) -> list[AssessmentResultModel]:
    """Bulk record results for an assessment.

    Args:
        assessment_id: The assessment to record results for.
        results_data: List of dicts with keys: enrollment_id, score (optional),
                      wrong_count (optional, for negative marking),
                      presence_status (default PRESENT), comments (optional).
        graded_by: User ID of the grader.

    Returns:
        List of created/updated AssessmentResultModel records.
    """
    assessment = AssessmentModel.query.get(assessment_id)
    if assessment is None:
        raise AssessmentError("Assessment not found.")

    results = []
    for item in results_data:
        enrollment_id = item.get("enrollment_id")
        if enrollment_id is None:
            raise AssessmentError("Each result must have an enrollment_id.")

        result = record_result(
            assessment_id=assessment_id,
            enrollment_id=enrollment_id,
            score=item.get("score"),
            wrong_count=item.get("wrong_count"),
            presence_status=item.get("presence_status", "PRESENT"),
            comments=item.get("comments", ""),
            graded_by=graded_by,
        )
        results.append(result)

    return results


def update_result(
    result_id: int,
    *,
    score: float | None = None,
    presence_status: str | None = None,
    comments: str | None = None,
    graded_by: int | None = None,
) -> AssessmentResultModel:
    """Update an existing assessment result."""
    result = AssessmentResultModel.query.get(result_id)
    if result is None:
        raise AssessmentError("Result not found.")

    assessment = AssessmentModel.query.get(result.assessment_id)
    if assessment is None:
        raise AssessmentError("Assessment not found.")

    max_score = float(assessment.max_score)
    passing_score = float(assessment.passing_score)

    new_presence = (
        presence_status if presence_status is not None else result.presence_status
    )
    new_score = (
        score
        if score is not None
        else (float(result.score) if result.score is not None else None)
    )

    if new_presence == "ABSENT":
        new_score = None
    elif new_score is not None:
        if new_score < 0:
            raise AssessmentError("Score cannot be negative.")
        if new_score > max_score:
            raise AssessmentError(f"Score cannot exceed maximum score of {max_score}.")

    percentage = None
    pass_fail = "NOT_DETERMINED"
    if new_score is not None and new_presence != "ABSENT":
        percentage = round(new_score / max_score * 100, 2)
        pass_fail = "PASS" if new_score >= passing_score else "FAIL"

    # Record history if score is being changed
    if result.result_status == "GRADED" and new_score is not None:
        _create_grade_history(
            result=result,
            new_score=new_score,
            new_pass_fail=pass_fail,
            corrected_by=graded_by,
            reason="Grade corrected",
        )

    # Capture old state for audit logging
    old_values = {
        "score": float(result.score) if result.score is not None else None,
        "percentage": float(result.percentage)
        if result.percentage is not None
        else None,
        "result_status": result.result_status,
        "presence_status": result.presence_status,
        "pass_fail": result.pass_fail,
        "comments": result.comments,
    }

    now = datetime.now()
    result.score = Decimal(str(new_score)) if new_score is not None else None
    result.percentage = Decimal(str(percentage)) if percentage is not None else None
    result.presence_status = new_presence
    result.pass_fail = pass_fail
    result.result_status = "GRADED" if new_score is not None else "NOT_GRADED"
    if comments is not None:
        result.comments = comments
    if graded_by is not None:
        result.graded_by = graded_by
        result.graded_at = now
    result.updated_at = now
    db.session.commit()

    # Audit log for grade correction
    if graded_by is not None:
        new_values = {
            "score": float(new_score) if new_score is not None else None,
            "percentage": round(percentage, 2) if percentage is not None else None,
            "result_status": result.result_status,
            "presence_status": new_presence,
            "pass_fail": pass_fail,
            "comments": comments if comments is not None else result.comments,
        }
        from app.application.audit.audit_service import log as audit_log

        audit_log(
            user_id=graded_by,
            action="UPDATE",
            entity_type="ASSESSMENT_RESULT",
            entity_id=result.id,
            old_values=old_values,
            new_values=new_values,
        )

    return result


def get_result(result_id: int) -> AssessmentResultModel | None:
    """Get a single result by ID."""
    return AssessmentResultModel.query.get(result_id)


def get_assessment_results(assessment_id: int) -> list[AssessmentResultModel]:
    """Get all results for an assessment."""
    return (
        AssessmentResultModel.query.filter_by(assessment_id=assessment_id)
        .order_by(AssessmentResultModel.student_user_id)
        .all()
    )


def get_student_results(student_user_id: int) -> list[AssessmentResultModel]:
    """Get all assessment results for a student across all classes."""
    return (
        AssessmentResultModel.query.filter_by(student_user_id=student_user_id)
        .order_by(AssessmentResultModel.created_at.desc())
        .all()
    )


def get_student_class_results(
    student_user_id: int, class_id: int
) -> list[AssessmentResultModel]:
    """Get assessment results for a student in a specific class."""
    return (
        AssessmentResultModel.query.filter_by(
            student_user_id=student_user_id,
        )
        .join(
            AssessmentModel, AssessmentResultModel.assessment_id == AssessmentModel.id
        )
        .filter(AssessmentModel.class_id == class_id)
        .order_by(AssessmentModel.scheduled_date.desc())
        .all()
    )


def get_class_results(class_id: int) -> list[AssessmentResultModel]:
    """Get all results for a class (across all assessments)."""
    return (
        AssessmentResultModel.query.join(
            AssessmentModel,
            AssessmentResultModel.assessment_id == AssessmentModel.id,
        )
        .filter(AssessmentModel.class_id == class_id)
        .order_by(AssessmentResultModel.student_user_id)
        .all()
    )


# ---------------------------------------------------------------------------
# Grade History
# ---------------------------------------------------------------------------


def get_grade_history(result_id: int) -> list[GradeHistoryModel]:
    """Get grade correction history for a result."""
    return (
        GradeHistoryModel.query.filter_by(result_id=result_id)
        .order_by(GradeHistoryModel.corrected_at.desc())
        .all()
    )


def _create_grade_history(
    *,
    result: AssessmentResultModel,
    new_score: float | None,
    new_pass_fail: str,
    corrected_by: int | None = None,
    reason: str = "",
) -> GradeHistoryModel:
    """Create a grade history entry for a correction."""
    history = GradeHistoryModel(
        result_id=result.id,
        previous_score=float(result.score) if result.score is not None else None,
        new_score=new_score,
        previous_pass_fail=result.pass_fail,
        new_pass_fail=new_pass_fail,
        corrected_by=corrected_by,
        reason=reason,
    )
    db.session.add(history)
    db.session.flush()
    return history


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def get_assessment_report(assessment_id: int) -> dict:
    """Generate assessment report with statistics."""
    assessment = AssessmentModel.query.get(assessment_id)
    if assessment is None:
        raise AssessmentError("Assessment not found.")

    results = get_assessment_results(assessment_id)
    eligible = get_eligible_enrollments(assessment_id)

    scores = []
    pass_count = 0
    fail_count = 0
    absent_count = 0
    not_graded_count = 0

    for r in results:
        if r.presence_status == "ABSENT":
            absent_count += 1
        elif r.result_status == "NOT_GRADED":
            not_graded_count += 1
        else:
            if r.score is not None:
                scores.append(float(r.score))
            if r.pass_fail == "PASS":
                pass_count += 1
            elif r.pass_fail == "FAIL":
                fail_count += 1

    graded_count = len(scores)
    average = round(sum(scores) / graded_count, 2) if graded_count > 0 else None
    highest = max(scores) if scores else None
    lowest = min(scores) if scores else None
    pass_rate = round(pass_count / graded_count * 100, 2) if graded_count > 0 else None

    return {
        "assessment": assessment,
        "total_eligible": len(eligible),
        "total_graded": graded_count,
        "total_absent": absent_count,
        "total_not_graded": not_graded_count,
        "average": average,
        "highest": highest,
        "lowest": lowest,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": pass_rate,
        "results": results,
    }


def get_student_academic_summary(student_user_id: int) -> dict:
    """Generate academic summary for a student across all classes."""
    results = get_student_results(student_user_id)

    total = len(results)
    graded = 0
    passed = 0
    failed = 0
    absent = 0
    scores = []

    for r in results:
        if r.presence_status == "ABSENT":
            absent += 1
        elif r.result_status in ("GRADED", "CORRECTED"):
            graded += 1
            if r.score is not None:
                scores.append(float(r.score))
            if r.pass_fail == "PASS":
                passed += 1
            elif r.pass_fail == "FAIL":
                failed += 1

    average = round(sum(scores) / len(scores), 2) if scores else None

    return {
        "total_assessments": total,
        "graded": graded,
        "passed": passed,
        "failed": failed,
        "absent": absent,
        "average": average,
        "results": results,
    }


def get_class_academic_summary(class_id: int) -> dict:
    """Generate academic summary for a class."""
    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        raise AssessmentError("Class not found.")

    assessments = list_class_assessments(class_id, include_cancelled=True)
    enrolled = EnrollmentModel.query.filter_by(
        class_id=class_id, status="APPROVED"
    ).count()
    all_results = get_class_results(class_id)

    total_results = len(all_results)
    graded = 0
    passed = 0
    failed = 0
    absent = 0
    scores = []

    for r in all_results:
        if r.presence_status == "ABSENT":
            absent += 1
        elif r.result_status in ("GRADED", "CORRECTED"):
            graded += 1
            if r.score is not None:
                scores.append(float(r.score))
            if r.pass_fail == "PASS":
                passed += 1
            elif r.pass_fail == "FAIL":
                failed += 1

    average = round(sum(scores) / len(scores), 2) if scores else None
    pass_rate = round(passed / graded * 100, 2) if graded > 0 else None

    return {
        "class": academy_class,
        "enrolled_count": enrolled,
        "total_assessments": len(assessments),
        "total_results": total_results,
        "graded": graded,
        "passed": passed,
        "failed": failed,
        "absent": absent,
        "average": average,
        "pass_rate": pass_rate,
        "assessments": assessments,
        "results": all_results,
    }


# ---------------------------------------------------------------------------
# CSV Export helpers
# ---------------------------------------------------------------------------


def get_assessment_csv_data(assessment_id: int) -> list[dict]:
    """Get assessment results formatted for CSV export."""
    assessment = AssessmentModel.query.get(assessment_id)
    if assessment is None:
        raise AssessmentError("Assessment not found.")

    results = get_assessment_results(assessment_id)

    rows = []

    for r in results:
        student = UserModel.query.get(r.student_user_id)
        profile = student.student_profile if student else None
        first_name = profile.first_name if profile else ""
        last_name = profile.last_name if profile else ""
        national_id = profile.national_id if profile else ""

        rows.append(
            {
                "student_id": r.student_user_id,
                "first_name": first_name,
                "last_name": last_name,
                "national_id": national_id,
                "score": float(r.score) if r.score is not None else "",
                "max_score": float(r.max_score),
                "percentage": float(r.percentage) if r.percentage is not None else "",
                "pass_fail": r.pass_fail,
                "presence": r.presence_status,
                "comments": r.comments,
            }
        )

    return rows


def get_student_csv_data(student_user_id: int) -> list[dict]:
    """Get student results formatted for CSV export."""
    results = get_student_results(student_user_id)
    rows = []

    for r in results:
        assessment = AssessmentModel.query.get(r.assessment_id)
        academy_class = (
            AcademyClassModel.query.get(assessment.class_id) if assessment else None
        )

        rows.append(
            {
                "assessment_title": assessment.title if assessment else "",
                "assessment_type": assessment.type if assessment else "",
                "class_title": academy_class.title if academy_class else "",
                "score": float(r.score) if r.score is not None else "",
                "max_score": float(r.max_score),
                "percentage": float(r.percentage) if r.percentage is not None else "",
                "pass_fail": r.pass_fail,
                "presence": r.presence_status,
            }
        )

    return rows


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
    return (
        EnrollmentModel.query.filter_by(
            student_user_id=student_user_id,
            class_id=class_id,
            status="APPROVED",
        ).first()
        is not None
    )


def is_parent_of_student(parent_user_id: int, student_user_id: int) -> bool:
    """Check if a parent is linked to a student."""
    parent_profile = ParentProfileModel.query.filter_by(user_id=parent_user_id).first()
    if parent_profile is None:
        return False
    return any(child.user_id == student_user_id for child in parent_profile.children)


def get_parent_children(parent_user_id: int) -> list[UserModel]:
    """Get all linked children for a parent."""
    parent_profile = ParentProfileModel.query.filter_by(user_id=parent_user_id).first()
    if parent_profile is None:
        return []
    return [
        UserModel.query.get(child.user_id)
        for child in parent_profile.children
        if UserModel.query.get(child.user_id) is not None
    ]


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


# ---------------------------------------------------------------------------
# P21 — Grading Templates & Weighted Grades
# ---------------------------------------------------------------------------

VALID_GRADING_TYPES = {
    "FINAL_EXAM",
    "MIDTERM",
    "QUIZ",
    "PROJECT",
    "PRACTICAL",
    "ORAL",
    "OTHER",
}


def create_grading_template(
    class_id: int,
    title: str,
    components: list[dict],
) -> GradingTemplateModel:
    """Create a grading template with weight components.

    Args:
        class_id: The class this template belongs to.
        title: Human-readable template title.
        components: List of dicts with keys: assessment_type, weight.

    Raises:
        AssessmentError: If validation fails (weights != 100%, invalid types).
    """
    if not title or not title.strip():
        raise AssessmentError("Grading template title is required.")

    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        raise AssessmentError("Class not found.")

    if not components:
        raise AssessmentError("At least one grading component is required.")

    total_weight = 0.0
    seen_types = set()
    for comp in components:
        atype = comp.get("assessment_type", "")
        weight = comp.get("weight", 0)

        if atype not in VALID_GRADING_TYPES:
            raise AssessmentError(f"Invalid assessment type: {atype}")
        if weight <= 0:
            raise AssessmentError(f"Weight must be positive for {atype}.")
        if atype in seen_types:
            raise AssessmentError(f"Duplicate assessment type: {atype}")

        seen_types.add(atype)
        total_weight += weight

    if abs(total_weight - 100.0) > 0.01:
        raise AssessmentError(f"Weights must sum to 100%, got {total_weight:.1f}%.")

    template = GradingTemplateModel(
        class_id=class_id,
        title=title.strip(),
    )
    db.session.add(template)
    db.session.flush()

    for comp in components:
        component = GradingComponentModel(
            template_id=template.id,
            assessment_type=comp["assessment_type"],
            weight=Decimal(str(comp["weight"])),
        )
        db.session.add(component)

    db.session.commit()
    return template


def update_grading_template(
    template_id: int,
    *,
    title: str | None = None,
    components: list[dict] | None = None,
) -> GradingTemplateModel:
    """Update a grading template and its components."""
    template = GradingTemplateModel.query.get(template_id)
    if template is None:
        raise AssessmentError("Grading template not found.")

    if title is not None:
        if not title.strip():
            raise AssessmentError("Grading template title cannot be empty.")
        template.title = title.strip()

    if components is not None:
        if not components:
            raise AssessmentError("At least one grading component is required.")

        total_weight = 0.0
        seen_types = set()
        for comp in components:
            atype = comp.get("assessment_type", "")
            weight = comp.get("weight", 0)

            if atype not in VALID_GRADING_TYPES:
                raise AssessmentError(f"Invalid assessment type: {atype}")
            if weight <= 0:
                raise AssessmentError(f"Weight must be positive for {atype}.")
            if atype in seen_types:
                raise AssessmentError(f"Duplicate assessment type: {atype}")

            seen_types.add(atype)
            total_weight += weight

        if abs(total_weight - 100.0) > 0.01:
            raise AssessmentError(f"Weights must sum to 100%, got {total_weight:.1f}%.")

        # Delete existing components and recreate
        GradingComponentModel.query.filter_by(template_id=template_id).delete()
        for comp in components:
            component = GradingComponentModel(
                template_id=template_id,
                assessment_type=comp["assessment_type"],
                weight=Decimal(str(comp["weight"])),
            )
            db.session.add(component)

    db.session.commit()
    return template


def get_grading_template(template_id: int) -> GradingTemplateModel | None:
    """Get a grading template by ID with its components."""
    return GradingTemplateModel.query.get(template_id)


def get_class_grading_template(
    class_id: int,
) -> GradingTemplateModel | None:
    """Get the grading template for a class (most recent if multiple)."""
    return (
        GradingTemplateModel.query.filter_by(class_id=class_id)
        .order_by(GradingTemplateModel.id.desc())
        .first()
    )


def calculate_final_grade(enrollment_id: int) -> dict:
    """Calculate the weighted final grade for a student in a class.

    Uses the class's GradingTemplate to compute a weighted average
    of all assessment results. Missing results are treated as 0.

    Args:
        enrollment_id: The enrollment to calculate for.

    Returns:
        dict with keys: final_grade, total_weight_covered, components, passed.
    """
    enrollment = EnrollmentModel.query.get(enrollment_id)
    if enrollment is None:
        raise AssessmentError("Enrollment not found.")

    template = get_class_grading_template(enrollment.class_id)
    if template is None:
        raise AssessmentError("No grading template defined for this class.")

    total_weighted_score = 0.0
    total_weight = 0.0
    component_results = []

    for component in template.components:
        weight = float(component.weight)

        # Get all graded results for this assessment type in the class
        results = (
            AssessmentResultModel.query.join(
                AssessmentModel,
                AssessmentModel.id == AssessmentResultModel.assessment_id,
            )
            .filter(
                AssessmentModel.class_id == enrollment.class_id,
                AssessmentModel.type == component.assessment_type,
                AssessmentResultModel.enrollment_id == enrollment_id,
                AssessmentResultModel.result_status.in_(["GRADED", "CORRECTED"]),
            )
            .all()
        )

        if results:
            # Average percentage for this type
            percentages = [
                float(r.percentage) for r in results if r.percentage is not None
            ]
            avg_percentage = sum(percentages) / len(percentages) if percentages else 0.0
        else:
            # Missing assessment = score of 0
            avg_percentage = 0.0

        weighted = avg_percentage * (weight / 100.0)
        total_weighted_score += weighted
        total_weight += weight

        component_results.append(
            {
                "type": component.assessment_type,
                "type_title": _assessment_type_title(component.assessment_type),
                "weight": weight,
                "avg_percentage": round(avg_percentage, 2),
                "weighted_score": round(weighted, 2),
                "result_count": len(results) if results else 0,
            }
        )

    final_grade = round(total_weighted_score, 2) if total_weight > 0 else None

    # Determine pass/fail based on class passing score (default 60)
    academy_class = AcademyClassModel.query.get(enrollment.class_id)
    passing_score = 60.0
    if academy_class and hasattr(academy_class, "passing_score"):
        passing_score = float(academy_class.passing_score)

    passed = final_grade is not None and final_grade >= passing_score

    return {
        "final_grade": final_grade,
        "total_weight_covered": total_weight,
        "components": component_results,
        "passed": passed,
    }


def _assessment_type_title(assessment_type: str) -> str:
    """Return Persian title for assessment type."""
    titles = {
        "FINAL_EXAM": "آزمون پایانی",
        "MIDTERM": "آزمون میان‌ترم",
        "QUIZ": "آزمون کلاسی",
        "PROJECT": "پروژه",
        "PRACTICAL": "عملی",
        "ORAL": "شفاهی",
        "OTHER": "سایر",
    }
    return titles.get(assessment_type, assessment_type)


# ---------------------------------------------------------------------------
# P21 — Transcript
# ---------------------------------------------------------------------------


def get_transcript_data(enrollment_id: int) -> dict:
    """Get comprehensive transcript data for a student in a class.

    Args:
        enrollment_id: The enrollment to generate transcript for.

    Returns:
        dict with student info, class info, assessment results, and final grade.
    """
    enrollment = EnrollmentModel.query.get(enrollment_id)
    if enrollment is None:
        raise AssessmentError("Enrollment not found.")

    academy_class = AcademyClassModel.query.get(enrollment.class_id)
    course = CourseModel.query.get(academy_class.course_id) if academy_class else None

    # Get student profile
    profile = StudentProfileModel.query.filter_by(
        user_id=enrollment.student_user_id
    ).first()

    # Get all results for this enrollment
    results = (
        AssessmentResultModel.query.join(
            AssessmentModel,
            AssessmentModel.id == AssessmentResultModel.assessment_id,
        )
        .filter(AssessmentResultModel.enrollment_id == enrollment_id)
        .order_by(AssessmentModel.scheduled_date, AssessmentModel.title)
        .all()
    )

    # Build result details
    result_details = []
    for r in results:
        assessment = AssessmentModel.query.get(r.assessment_id)
        result_details.append(
            {
                "assessment_title": assessment.title if assessment else "",
                "assessment_type": assessment.type if assessment else "",
                "assessment_type_title": (
                    _assessment_type_title(assessment.type) if assessment else ""
                ),
                "score": float(r.score) if r.score is not None else None,
                "wrong_count": r.wrong_count,
                "max_score": float(r.max_score),
                "percentage": float(r.percentage) if r.percentage is not None else None,
                "pass_fail": r.pass_fail,
                "presence_status": r.presence_status,
                "comments": r.comments,
            }
        )

    # Calculate final grade
    try:
        final_grade_data = calculate_final_grade(enrollment_id)
    except AssessmentError:
        final_grade_data = {
            "final_grade": None,
            "total_weight_covered": 0,
            "components": [],
            "passed": False,
        }

    return {
        "student_name": f"{profile.first_name} {profile.last_name}" if profile else "",
        "student_national_id": profile.national_id if profile else "",
        "class_title": academy_class.title if academy_class else "",
        "course_title": course.title if course else "",
        "results": result_details,
        "final_grade": final_grade_data["final_grade"],
        "passed": final_grade_data["passed"],
        "components": final_grade_data["components"],
    }
