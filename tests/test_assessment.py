"""Tests for P7 — Exams, Assessments & Grades."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from app import create_app
from app.application.assessment import assessment_service
from app.extensions import db as _db
from app.infrastructure.database.models import (
    AcademyClassModel,
    CourseModel,
    EnrollmentModel,
    RoleModel,
    StudentProfileModel,
    TeacherProfileModel,
    UserModel,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def app():
    app = create_app("testing")
    return app


@pytest.fixture(scope="function")
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def admin_user(db):
    user = UserModel(login="admin")
    user.set_password("adminpass")
    role = RoleModel(name="ADMIN")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def teacher_user(db):
    user = UserModel(login="teacher")
    user.set_password("teacherpass")
    role = RoleModel(name="TEACHER")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.flush()
    profile = TeacherProfileModel(
        user_id=user.id,
        first_name="Teacher",
        last_name="One",
        national_id="T1234567890",
        mobile_phone="09120000001",
    )
    db.session.add(profile)
    db.session.commit()
    return user


@pytest.fixture
def student_user(db):
    user = UserModel(login="student")
    user.set_password("studentpass")
    role = RoleModel(name="STUDENT")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.flush()
    profile = StudentProfileModel(
        user_id=user.id,
        first_name="Ali",
        last_name="Rezaei",
        national_id="1234567890",
        mobile_phone="09121234567",
        birth_date=date(2000, 1, 15),
        gender="MALE",
    )
    db.session.add(profile)
    db.session.commit()
    return user


@pytest.fixture
def student_user2(db):
    user = UserModel(login="student2")
    user.set_password("studentpass2")
    role = RoleModel.query.get("STUDENT")
    if role is None:
        role = RoleModel(name="STUDENT")
        db.session.add(role)
        db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.flush()
    profile = StudentProfileModel(
        user_id=user.id,
        first_name="Sara",
        last_name="Ahmadi",
        national_id="0987654321",
        mobile_phone="09121234568",
        birth_date=date(2001, 5, 20),
        gender="FEMALE",
    )
    db.session.add(profile)
    db.session.commit()
    return user


@pytest.fixture
def parent_user(db):
    user = UserModel(login="parent")
    user.set_password("parentpass")
    role = RoleModel(name="PARENT")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def course(db):
    c = CourseModel(title="Python Course", description="Learn Python", num_sessions=10)
    db.session.add(c)
    db.session.commit()
    return c


@pytest.fixture
def academy_class(db, course, teacher_user):
    c = AcademyClassModel(
        course_id=course.id,
        title="Python Class A",
        start_date=date(2026, 1, 1),
        capacity=30,
        num_sessions=10,
        status="ACTIVE",
        teacher_user_id=teacher_user.id,
    )
    db.session.add(c)
    db.session.commit()
    return c


@pytest.fixture
def enrollment(db, student_user, academy_class):
    e = EnrollmentModel(
        student_user_id=student_user.id,
        class_id=academy_class.id,
        status="APPROVED",
        approved_at=datetime.now(),
    )
    db.session.add(e)
    db.session.commit()
    return e


@pytest.fixture
def enrollment2(db, student_user2, academy_class):
    e = EnrollmentModel(
        student_user_id=student_user2.id,
        class_id=academy_class.id,
        status="APPROVED",
        approved_at=datetime.now(),
    )
    db.session.add(e)
    db.session.commit()
    return e


@pytest.fixture
def assessment(db, academy_class, admin_user):
    a = assessment_service.create_assessment(
        class_id=academy_class.id,
        assessment_type="FINAL_EXAM",
        title="Final Exam",
        description="End of course exam",
        scheduled_date=date(2026, 6, 15),
        max_score=100,
        passing_score=60,
        status="DRAFT",
        created_by=admin_user.id,
    )
    return a


# ---------------------------------------------------------------------------
# Assessment CRUD Tests
# ---------------------------------------------------------------------------


class TestAssessmentCRUD:
    def test_create_assessment(self, db, academy_class, admin_user):
        a = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="FINAL_EXAM",
            title="Final Exam",
            max_score=100,
            passing_score=60,
            created_by=admin_user.id,
        )
        assert a.id is not None
        assert a.title == "Final Exam"
        assert a.type == "FINAL_EXAM"
        assert a.max_score == Decimal("100")
        assert a.passing_score == Decimal("60")
        assert a.status == "DRAFT"

    def test_create_midterm(self, db, academy_class, admin_user):
        a = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="MIDTERM",
            title="Midterm",
            max_score=50,
            passing_score=25,
        )
        assert a.type == "MIDTERM"
        assert a.max_score == Decimal("50")

    def test_create_quiz(self, db, academy_class, admin_user):
        a = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="QUIZ",
            title="Quiz 1",
        )
        assert a.type == "QUIZ"

    def test_create_invalid_type_raises_error(self, db, academy_class):
        with pytest.raises(
            assessment_service.AssessmentError, match="Invalid assessment type"
        ):
            assessment_service.create_assessment(
                class_id=academy_class.id,
                assessment_type="INVALID",
                title="Bad",
            )

    def test_create_empty_title_raises_error(self, db, academy_class):
        with pytest.raises(
            assessment_service.AssessmentError, match="title is required"
        ):
            assessment_service.create_assessment(
                class_id=academy_class.id,
                assessment_type="FINAL_EXAM",
                title="",
            )

    def test_create_whitespace_title_raises_error(self, db, academy_class):
        with pytest.raises(
            assessment_service.AssessmentError, match="title is required"
        ):
            assessment_service.create_assessment(
                class_id=academy_class.id,
                assessment_type="FINAL_EXAM",
                title="   ",
            )

    def test_create_nonexistent_class_raises_error(self, db):
        with pytest.raises(assessment_service.AssessmentError, match="Class not found"):
            assessment_service.create_assessment(
                class_id=9999,
                assessment_type="FINAL_EXAM",
                title="Bad",
            )

    def test_create_max_score_zero_raises_error(self, db, academy_class):
        with pytest.raises(
            assessment_service.AssessmentError, match="Maximum score must be positive"
        ):
            assessment_service.create_assessment(
                class_id=academy_class.id,
                assessment_type="FINAL_EXAM",
                title="Bad",
                max_score=0,
            )

    def test_create_negative_passing_score_raises_error(self, db, academy_class):
        with pytest.raises(
            assessment_service.AssessmentError, match="Passing score cannot be negative"
        ):
            assessment_service.create_assessment(
                class_id=academy_class.id,
                assessment_type="FINAL_EXAM",
                title="Bad",
                passing_score=-1,
            )

    def test_create_passing_score_exceeds_max_raises_error(self, db, academy_class):
        with pytest.raises(
            assessment_service.AssessmentError, match="Passing score cannot exceed"
        ):
            assessment_service.create_assessment(
                class_id=academy_class.id,
                assessment_type="FINAL_EXAM",
                title="Bad",
                max_score=50,
                passing_score=60,
            )

    def test_update_assessment(self, db, assessment):
        updated = assessment_service.update_assessment(
            assessment, title="Updated Exam", max_score=150, passing_score=75
        )
        assert updated.title == "Updated Exam"
        assert updated.max_score == Decimal("150")
        assert updated.passing_score == Decimal("75")

    def test_update_passing_score_auto_adjusts(self, db, assessment):
        updated = assessment_service.update_assessment(assessment, max_score=50)
        # passing_score was 60, max is now 50, so passing should be capped
        assert updated.passing_score == Decimal("50")

    def test_get_assessment(self, db, assessment):
        found = assessment_service.get_assessment(assessment.id)
        assert found is not None
        assert found.id == assessment.id

    def test_get_nonexistent_assessment(self, db):
        found = assessment_service.get_assessment(9999)
        assert found is None

    def test_list_class_assessments(self, db, academy_class, assessment):
        assessments = assessment_service.list_class_assessments(academy_class.id)
        assert len(assessments) == 1
        assert assessments[0].id == assessment.id

    def test_list_excludes_cancelled(self, db, academy_class, assessment):
        assessment_service.cancel_assessment(assessment)
        assessments = assessment_service.list_class_assessments(academy_class.id)
        assert len(assessments) == 0

    def test_list_includes_cancelled_when_flagged(self, db, academy_class, assessment):
        assessment_service.cancel_assessment(assessment)
        assessments = assessment_service.list_class_assessments(
            academy_class.id, include_cancelled=True
        )
        assert len(assessments) == 1


# ---------------------------------------------------------------------------
# Assessment Status Transitions
# ---------------------------------------------------------------------------


class TestAssessmentStatus:
    def test_draft_to_scheduled(self, db, assessment):
        updated = assessment_service.update_assessment_status(assessment, "SCHEDULED")
        assert updated.status == "SCHEDULED"

    def test_scheduled_to_open(self, db, assessment):
        assessment_service.update_assessment_status(assessment, "SCHEDULED")
        updated = assessment_service.update_assessment_status(assessment, "OPEN")
        assert updated.status == "OPEN"

    def test_open_to_closed(self, db, assessment):
        assessment_service.update_assessment_status(assessment, "SCHEDULED")
        assessment_service.update_assessment_status(assessment, "OPEN")
        updated = assessment_service.update_assessment_status(assessment, "CLOSED")
        assert updated.status == "CLOSED"

    def test_closed_to_graded(self, db, assessment):
        assessment_service.update_assessment_status(assessment, "SCHEDULED")
        assessment_service.update_assessment_status(assessment, "OPEN")
        assessment_service.update_assessment_status(assessment, "CLOSED")
        updated = assessment_service.update_assessment_status(assessment, "GRADED")
        assert updated.status == "GRADED"

    def test_draft_to_cancelled(self, db, assessment):
        updated = assessment_service.update_assessment_status(assessment, "CANCELLED")
        assert updated.status == "CANCELLED"

    def test_invalid_transition_raises_error(self, db, assessment):
        with pytest.raises(
            assessment_service.AssessmentError, match="Cannot transition"
        ):
            assessment_service.update_assessment_status(assessment, "OPEN")

    def test_cancel_assessment(self, db, assessment):
        cancelled = assessment_service.cancel_assessment(assessment)
        assert cancelled.status == "CANCELLED"

    def test_double_cancel_raises_error(self, db, assessment):
        assessment_service.cancel_assessment(assessment)
        with pytest.raises(
            assessment_service.AssessmentError, match="already cancelled"
        ):
            assessment_service.cancel_assessment(assessment)

    def test_reschedule_assessment(self, db, assessment):
        new_date = date(2026, 7, 1)
        updated = assessment_service.reschedule_assessment(assessment, new_date)
        assert updated.scheduled_date == new_date
        assert updated.status == "SCHEDULED"

    def test_reschedule_cancelled_raises_error(self, db, assessment):
        assessment_service.cancel_assessment(assessment)
        with pytest.raises(assessment_service.AssessmentError, match="cancelled"):
            assessment_service.reschedule_assessment(assessment, date(2026, 7, 1))


# ---------------------------------------------------------------------------
# Assessment Eligibility
# ---------------------------------------------------------------------------


class TestAssessmentEligibility:
    def test_eligible_students(self, db, assessment, enrollment):
        eligible = assessment_service.get_eligible_enrollments(assessment.id)
        assert len(eligible) == 1
        assert eligible[0].id == enrollment.id

    def test_excludes_pending_enrollment(
        self, db, assessment, student_user2, academy_class
    ):
        pending = EnrollmentModel(
            student_user_id=student_user2.id,
            class_id=academy_class.id,
            status="PENDING",
        )
        db.session.add(pending)
        db.session.commit()

        eligible = assessment_service.get_eligible_enrollments(assessment.id)
        assert len(eligible) == 0

    def test_excludes_cancelled_enrollment(self, db, assessment, enrollment):
        enrollment.status = "CANCELLED"
        db.session.commit()

        eligible = assessment_service.get_eligible_enrollments(assessment.id)
        assert len(eligible) == 0

    def test_nonexistent_assessment_raises_error(self, db):
        with pytest.raises(
            assessment_service.AssessmentError, match="Assessment not found"
        ):
            assessment_service.get_eligible_enrollments(9999)


# ---------------------------------------------------------------------------
# Assessment Results
# ---------------------------------------------------------------------------


class TestAssessmentResults:
    def test_record_result(self, db, assessment, enrollment):
        r = assessment_service.record_result(assessment.id, enrollment.id, score=85)
        assert r.id is not None
        assert r.score == Decimal("85")
        assert r.percentage == Decimal("85.00")
        assert r.pass_fail == "PASS"
        assert r.result_status == "GRADED"

    def test_record_zero_score(self, db, assessment, enrollment):
        r = assessment_service.record_result(assessment.id, enrollment.id, score=0)
        assert r.score == Decimal("0")
        assert r.pass_fail == "FAIL"

    def test_record_maximum_score(self, db, assessment, enrollment):
        r = assessment_service.record_result(assessment.id, enrollment.id, score=100)
        assert r.score == Decimal("100")
        assert r.pass_fail == "PASS"
        assert r.percentage == Decimal("100.00")

    def test_record_absent(self, db, assessment, enrollment):
        r = assessment_service.record_result(
            assessment.id, enrollment.id, presence_status="ABSENT"
        )
        assert r.score is None
        assert r.presence_status == "ABSENT"
        assert r.pass_fail == "NOT_DETERMINED"

    def test_record_excused(self, db, assessment, enrollment):
        r = assessment_service.record_result(
            assessment.id, enrollment.id, presence_status="EXCUSED"
        )
        assert r.presence_status == "EXCUSED"

    def test_score_above_max_raises_error(self, db, assessment, enrollment):
        with pytest.raises(
            assessment_service.AssessmentError, match="Score cannot exceed"
        ):
            assessment_service.record_result(assessment.id, enrollment.id, score=101)

    def test_negative_score_raises_error(self, db, assessment, enrollment):
        with pytest.raises(
            assessment_service.AssessmentError, match="Score cannot be negative"
        ):
            assessment_service.record_result(assessment.id, enrollment.id, score=-1)

    def test_invalid_presence_status_raises_error(self, db, assessment, enrollment):
        with pytest.raises(
            assessment_service.AssessmentError, match="Invalid presence status"
        ):
            assessment_service.record_result(
                assessment.id, enrollment.id, presence_status="INVALID"
            )

    def test_result_for_nonexistent_enrollment_raises_error(self, db, assessment):
        with pytest.raises(
            assessment_service.AssessmentError, match="Enrollment not found"
        ):
            assessment_service.record_result(assessment.id, 9999, score=80)

    def test_result_for_wrong_class_enrollment_raises_error(
        self, db, assessment, course, teacher_user
    ):
        other_class = AcademyClassModel(
            course_id=course.id,
            title="Other Class",
            start_date=date(2026, 1, 1),
            capacity=30,
            num_sessions=10,
            status="ACTIVE",
        )
        db.session.add(other_class)
        db.session.flush()
        other_student = UserModel(login="other")
        other_student.set_password("pass")
        db.session.add(other_student)
        db.session.flush()
        other_enrollment = EnrollmentModel(
            student_user_id=other_student.id,
            class_id=other_class.id,
            status="APPROVED",
        )
        db.session.add(other_enrollment)
        db.session.commit()

        with pytest.raises(assessment_service.AssessmentError, match="does not belong"):
            assessment_service.record_result(
                assessment.id, other_enrollment.id, score=80
            )

    def test_result_for_pending_enrollment_raises_error(
        self, db, assessment, student_user2, academy_class
    ):
        pending = EnrollmentModel(
            student_user_id=student_user2.id,
            class_id=academy_class.id,
            status="PENDING",
        )
        db.session.add(pending)
        db.session.commit()

        with pytest.raises(
            assessment_service.AssessmentError, match="approved enrollments"
        ):
            assessment_service.record_result(assessment.id, pending.id, score=80)

    def test_update_existing_result(self, db, assessment, enrollment):
        r1 = assessment_service.record_result(assessment.id, enrollment.id, score=70)
        r2 = assessment_service.record_result(assessment.id, enrollment.id, score=85)
        assert r1.id == r2.id
        assert r2.score == Decimal("85")
        assert r2.pass_fail == "PASS"

    def test_pass_fail_calculation_pass(self, db, assessment, enrollment):
        r = assessment_service.record_result(assessment.id, enrollment.id, score=60)
        assert r.pass_fail == "PASS"

    def test_pass_fail_calculation_fail(self, db, assessment, enrollment):
        r = assessment_service.record_result(assessment.id, enrollment.id, score=59)
        assert r.pass_fail == "FAIL"

    def test_custom_max_score(self, db, academy_class, admin_user, enrollment):
        a = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="QUIZ",
            title="Quiz",
            max_score=50,
            passing_score=25,
        )
        r = assessment_service.record_result(a.id, enrollment.id, score=30)
        assert r.max_score == Decimal("50")
        assert r.percentage == Decimal("60.00")
        assert r.pass_fail == "PASS"

    def test_result_with_comments(self, db, assessment, enrollment):
        r = assessment_service.record_result(
            assessment.id, enrollment.id, score=85, comments="Good work"
        )
        assert r.comments == "Good work"


# ---------------------------------------------------------------------------
# Bulk Grading
# ---------------------------------------------------------------------------


class TestBulkGrading:
    def test_bulk_record(self, db, assessment, enrollment, enrollment2):
        data = [
            {"enrollment_id": enrollment.id, "score": 80},
            {"enrollment_id": enrollment2.id, "score": 90},
        ]
        results = assessment_service.record_bulk_results(
            assessment.id, data, graded_by=None
        )
        assert len(results) == 2
        assert results[0].score == Decimal("80")
        assert results[1].score == Decimal("90")

    def test_bulk_mixed_scores_and_absence(
        self, db, assessment, enrollment, enrollment2
    ):
        data = [
            {"enrollment_id": enrollment.id, "score": 80},
            {"enrollment_id": enrollment2.id, "presence_status": "ABSENT"},
        ]
        results = assessment_service.record_bulk_results(assessment.id, data)
        assert len(results) == 2
        assert results[0].score == Decimal("80")
        assert results[1].score is None
        assert results[1].presence_status == "ABSENT"

    def test_bulk_missing_enrollment_id_raises_error(self, db, assessment):
        with pytest.raises(assessment_service.AssessmentError, match="enrollment_id"):
            assessment_service.record_bulk_results(assessment.id, [{"score": 80}])

    def test_bulk_updates_existing(self, db, assessment, enrollment, enrollment2):
        assessment_service.record_result(assessment.id, enrollment.id, score=70)
        data = [
            {"enrollment_id": enrollment.id, "score": 85},
            {"enrollment_id": enrollment2.id, "score": 90},
        ]
        results = assessment_service.record_bulk_results(assessment.id, data)
        # enrollment.id result should be updated, not duplicated
        assert results[0].score == Decimal("85")


# ---------------------------------------------------------------------------
# Grade History
# ---------------------------------------------------------------------------


class TestGradeHistory:
    def test_correction_creates_history(self, db, assessment, enrollment):
        assessment_service.record_result(assessment.id, enrollment.id, score=70)
        assessment_service.record_result(assessment.id, enrollment.id, score=80)

        result = assessment_service.get_assessment_results(assessment.id)[0]
        history = assessment_service.get_grade_history(result.id)
        assert len(history) == 1
        assert history[0].previous_score == 70.0
        assert history[0].new_score == 80.0

    def test_multiple_corrections(self, db, assessment, enrollment):
        assessment_service.record_result(assessment.id, enrollment.id, score=60)
        assessment_service.record_result(assessment.id, enrollment.id, score=70)
        assessment_service.record_result(assessment.id, enrollment.id, score=80)

        result = assessment_service.get_assessment_results(assessment.id)[0]
        history = assessment_service.get_grade_history(result.id)
        assert len(history) == 2

    def test_history_preserves_metadata(self, db, assessment, enrollment, admin_user):
        assessment_service.record_result(
            assessment.id, enrollment.id, score=70, graded_by=admin_user.id
        )
        assessment_service.record_result(
            assessment.id, enrollment.id, score=80, graded_by=admin_user.id
        )

        result = assessment_service.get_assessment_results(assessment.id)[0]
        history = assessment_service.get_grade_history(result.id)
        assert history[0].corrected_by == admin_user.id
        assert history[0].reason == "Grade updated"

    def test_update_result_creates_history(self, db, assessment, enrollment):
        assessment_service.record_result(assessment.id, enrollment.id, score=70)
        result = assessment_service.get_assessment_results(assessment.id)[0]
        assessment_service.update_result(result.id, score=85)

        history = assessment_service.get_grade_history(result.id)
        assert len(history) == 1
        assert history[0].previous_score == 70.0
        assert history[0].new_score == 85.0


# ---------------------------------------------------------------------------
# Teacher Authorization
# ---------------------------------------------------------------------------


class TestTeacherAuthorization:
    def test_teacher_of_class(self, db, teacher_user, academy_class):
        assert assessment_service.is_teacher_of_class(teacher_user.id, academy_class.id)

    def test_not_teacher_of_class(self, db, teacher_user, course):
        other_class = AcademyClassModel(
            course_id=course.id,
            title="Other",
            start_date=date(2026, 1, 1),
            capacity=30,
            num_sessions=10,
            status="ACTIVE",
        )
        db.session.add(other_class)
        db.session.commit()
        assert not assessment_service.is_teacher_of_class(
            teacher_user.id, other_class.id
        )

    def test_nonexistent_class(self, db, teacher_user):
        assert not assessment_service.is_teacher_of_class(teacher_user.id, 9999)


# ---------------------------------------------------------------------------
# Student Authorization
# ---------------------------------------------------------------------------


class TestStudentAuthorization:
    def test_student_enrolled(self, db, student_user, academy_class, enrollment):
        assert assessment_service.is_student_enrolled(student_user.id, academy_class.id)

    def test_student_not_enrolled(self, db, student_user, course):
        other_class = AcademyClassModel(
            course_id=course.id,
            title="Other",
            start_date=date(2026, 1, 1),
            capacity=30,
            num_sessions=10,
            status="ACTIVE",
        )
        db.session.add(other_class)
        db.session.commit()
        assert not assessment_service.is_student_enrolled(
            student_user.id, other_class.id
        )


# ---------------------------------------------------------------------------
# Parent Authorization
# ---------------------------------------------------------------------------


class TestParentAuthorization:
    def test_parent_of_student(self, db, parent_user, student_user):
        from app.infrastructure.database.models import ParentProfileModel

        profile = ParentProfileModel(
            user_id=parent_user.id,
            first_name="Parent",
            last_name="One",
            national_id="P1234567890",
            mobile_phone="09120000002",
        )
        db.session.add(profile)
        db.session.flush()
        profile.children.append(student_user.student_profile)
        db.session.commit()

        assert assessment_service.is_parent_of_student(parent_user.id, student_user.id)

    def test_not_parent_of_student(self, db, parent_user, student_user):
        assert not assessment_service.is_parent_of_student(
            parent_user.id, student_user.id
        )


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


class TestReports:
    def test_assessment_report(self, db, assessment, enrollment, enrollment2):
        assessment_service.record_result(assessment.id, enrollment.id, score=80)
        assessment_service.record_result(assessment.id, enrollment2.id, score=60)

        report = assessment_service.get_assessment_report(assessment.id)
        assert report["total_eligible"] == 2
        assert report["total_graded"] == 2
        assert report["average"] == 70.0
        assert report["highest"] == 80.0
        assert report["lowest"] == 60.0
        assert report["pass_count"] == 2
        assert report["fail_count"] == 0
        assert report["pass_rate"] == 100.0

    def test_assessment_report_with_absent(
        self, db, assessment, enrollment, enrollment2
    ):
        assessment_service.record_result(assessment.id, enrollment.id, score=80)
        assessment_service.record_result(
            assessment.id, enrollment2.id, presence_status="ABSENT"
        )

        report = assessment_service.get_assessment_report(assessment.id)
        assert report["total_graded"] == 1
        assert report["total_absent"] == 1
        assert report["average"] == 80.0

    def test_assessment_report_no_results(self, db, assessment):
        report = assessment_service.get_assessment_report(assessment.id)
        assert report["total_graded"] == 0
        assert report["average"] is None
        assert report["pass_rate"] is None

    def test_student_academic_summary(
        self, db, assessment, enrollment, academy_class, admin_user
    ):
        assessment_service.record_result(assessment.id, enrollment.id, score=85)

        a2 = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="QUIZ",
            title="Quiz 1",
        )
        assessment_service.record_result(a2.id, enrollment.id, score=90)

        summary = assessment_service.get_student_academic_summary(
            enrollment.student_user_id
        )
        assert summary["total_assessments"] == 2
        assert summary["graded"] == 2
        assert summary["passed"] == 2
        assert summary["average"] == 87.5

    def test_class_academic_summary(self, db, assessment, enrollment, enrollment2):
        assessment_service.record_result(assessment.id, enrollment.id, score=80)
        assessment_service.record_result(assessment.id, enrollment2.id, score=60)

        summary = assessment_service.get_class_academic_summary(assessment.class_id)
        assert summary["enrolled_count"] == 2
        assert summary["total_assessments"] == 1
        assert summary["average"] == 70.0
        assert summary["pass_rate"] == 100.0

    def test_class_report_nonexistent_class(self, db):
        with pytest.raises(assessment_service.AssessmentError, match="Class not found"):
            assessment_service.get_class_academic_summary(9999)


# ---------------------------------------------------------------------------
# CSV Export
# ---------------------------------------------------------------------------


class TestCSVExport:
    def test_assessment_csv_data(self, db, assessment, enrollment):
        assessment_service.record_result(assessment.id, enrollment.id, score=85)

        rows = assessment_service.get_assessment_csv_data(assessment.id)
        assert len(rows) == 1
        assert rows[0]["score"] == 85.0
        assert rows[0]["pass_fail"] == "PASS"

    def test_student_csv_data(self, db, assessment, enrollment):
        assessment_service.record_result(assessment.id, enrollment.id, score=85)

        rows = assessment_service.get_student_csv_data(enrollment.student_user_id)
        assert len(rows) == 1
        assert rows[0]["score"] == 85.0


# ---------------------------------------------------------------------------
# Domain Entity Tests
# ---------------------------------------------------------------------------


class TestDomainEntities:
    def test_assessment_repr(self, db, academy_class, admin_user):
        from app.domain.assessment import Assessment, AssessmentType

        a = Assessment(
            id=1,
            class_id=academy_class.id,
            assessment_type=AssessmentType.FINAL_EXAM,
            title="Test",
        )
        assert "FINAL_EXAM" in repr(a)
        assert "Test" in repr(a)

    def test_assessment_status_transitions(self):
        from app.domain.assessment import Assessment, AssessmentStatus, AssessmentType

        a = Assessment(
            id=1,
            class_id=1,
            assessment_type=AssessmentType.FINAL_EXAM,
            title="Test",
            status=AssessmentStatus.DRAFT,
        )
        assert a.can_transition_to(AssessmentStatus.SCHEDULED)
        assert a.can_transition_to(AssessmentStatus.CANCELLED)
        assert not a.can_transition_to(AssessmentStatus.OPEN)

    def test_result_repr(self):
        from app.domain.result import (
            AssessmentResult,
        )

        r = AssessmentResult(
            id=1,
            assessment_id=1,
            enrollment_id=1,
            student_user_id=1,
            score=85,
        )
        assert "85" in repr(r)

    def test_grade_history_repr(self):
        from app.domain.result import GradeHistory

        h = GradeHistory(
            id=1,
            result_id=1,
            previous_score=70,
            new_score=80,
            previous_pass_fail="PASS",
            new_pass_fail="PASS",
        )
        assert "70" in repr(h)
        assert "80" in repr(h)


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_full_lifecycle(
        self, db, academy_class, admin_user, student_user, enrollment
    ):
        """Test complete assessment lifecycle from creation to grading."""
        # Create
        a = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="FINAL_EXAM",
            title="Final Exam",
            max_score=100,
            passing_score=60,
            created_by=admin_user.id,
        )
        assert a.status == "DRAFT"

        # Schedule
        assessment_service.update_assessment_status(a, "SCHEDULED")
        assert a.status == "SCHEDULED"

        # Open
        assessment_service.update_assessment_status(a, "OPEN")
        assert a.status == "OPEN"

        # Grade
        r = assessment_service.record_result(a.id, enrollment.id, score=85)
        assert r.pass_fail == "PASS"

        # Close
        assessment_service.update_assessment_status(a, "CLOSED")
        assert a.status == "CLOSED"

        # Mark graded
        assessment_service.update_assessment_status(a, "GRADED")
        assert a.status == "GRADED"

        # Verify report
        report = assessment_service.get_assessment_report(a.id)
        assert report["total_graded"] == 1
        assert report["average"] == 85.0

    def test_historical_results_preserved_on_enrollment_cancel(
        self, db, assessment, enrollment
    ):
        """Test that results survive enrollment cancellation."""
        assessment_service.record_result(assessment.id, enrollment.id, score=85)

        # Cancel enrollment
        enrollment.status = "CANCELLED"
        db.session.commit()

        # Result should still exist
        results = assessment_service.get_assessment_results(assessment.id)
        assert len(results) == 1
        assert results[0].score == Decimal("85")


# ---------------------------------------------------------------------------
# P21 — Advanced Grading & Transcripts
# ---------------------------------------------------------------------------


class TestGradingTemplate:
    """Tests for grading template CRUD."""

    def test_create_grading_template(self, db, admin_user, academy_class):
        template = assessment_service.create_grading_template(
            class_id=academy_class.id,
            title="فرمول ارزیابی پاییز",
            components=[
                {"assessment_type": "FINAL_EXAM", "weight": 50},
                {"assessment_type": "MIDTERM", "weight": 30},
                {"assessment_type": "QUIZ", "weight": 20},
            ],
        )
        assert template.id is not None
        assert template.class_id == academy_class.id
        assert template.title == "فرمول ارزیابی پاییز"

    def test_create_grading_template_weights_not_100_raises(
        self, db, admin_user, academy_class
    ):
        with pytest.raises(assessment_service.AssessmentError, match="100%"):
            assessment_service.create_grading_template(
                class_id=academy_class.id,
                title="Invalid",
                components=[
                    {"assessment_type": "FINAL_EXAM", "weight": 50},
                    {"assessment_type": "MIDTERM", "weight": 30},
                ],
            )

    def test_create_grading_template_empty_title_raises(
        self, db, admin_user, academy_class
    ):
        with pytest.raises(assessment_service.AssessmentError, match="title"):
            assessment_service.create_grading_template(
                class_id=academy_class.id,
                title="",
                components=[{"assessment_type": "FINAL_EXAM", "weight": 100}],
            )

    def test_create_grading_template_no_components_raises(
        self, db, admin_user, academy_class
    ):
        with pytest.raises(assessment_service.AssessmentError, match="component"):
            assessment_service.create_grading_template(
                class_id=academy_class.id,
                title="Empty",
                components=[],
            )

    def test_create_grading_template_invalid_type_raises(
        self, db, admin_user, academy_class
    ):
        with pytest.raises(assessment_service.AssessmentError, match="Invalid"):
            assessment_service.create_grading_template(
                class_id=academy_class.id,
                title="Invalid Type",
                components=[{"assessment_type": "INVALID", "weight": 100}],
            )

    def test_create_grading_template_duplicate_type_raises(
        self, db, admin_user, academy_class
    ):
        with pytest.raises(assessment_service.AssessmentError, match="Duplicate"):
            assessment_service.create_grading_template(
                class_id=academy_class.id,
                title="Duplicate",
                components=[
                    {"assessment_type": "FINAL_EXAM", "weight": 50},
                    {"assessment_type": "FINAL_EXAM", "weight": 50},
                ],
            )

    def test_create_grading_template_negative_weight_raises(
        self, db, admin_user, academy_class
    ):
        with pytest.raises(assessment_service.AssessmentError, match="positive"):
            assessment_service.create_grading_template(
                class_id=academy_class.id,
                title="Negative",
                components=[{"assessment_type": "FINAL_EXAM", "weight": -10}],
            )

    def test_update_grading_template(self, db, admin_user, academy_class):
        template = assessment_service.create_grading_template(
            class_id=academy_class.id,
            title="Original",
            components=[{"assessment_type": "FINAL_EXAM", "weight": 100}],
        )
        updated = assessment_service.update_grading_template(
            template.id,
            title="Updated",
            components=[
                {"assessment_type": "FINAL_EXAM", "weight": 60},
                {"assessment_type": "QUIZ", "weight": 40},
            ],
        )
        assert updated.title == "Updated"
        assert len(updated.components) == 2

    def test_get_grading_template(self, db, academy_class):
        template = assessment_service.create_grading_template(
            class_id=academy_class.id,
            title="Test",
            components=[{"assessment_type": "FINAL_EXAM", "weight": 100}],
        )
        result = assessment_service.get_grading_template(template.id)
        assert result is not None
        assert result.id == template.id

    def test_get_class_grading_template(self, db, academy_class):
        template = assessment_service.create_grading_template(
            class_id=academy_class.id,
            title="Test",
            components=[{"assessment_type": "FINAL_EXAM", "weight": 100}],
        )
        result = assessment_service.get_class_grading_template(academy_class.id)
        assert result is not None
        assert result.id == template.id


class TestCalculateFinalGrade:
    """Tests for weighted grade calculation."""

    def test_calculate_final_grade_basic(self, db, academy_class, enrollment):
        # Create grading template
        assessment_service.create_grading_template(
            class_id=academy_class.id,
            title="Test",
            components=[
                {"assessment_type": "FINAL_EXAM", "weight": 60},
                {"assessment_type": "QUIZ", "weight": 40},
            ],
        )

        # Create assessments
        final = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="FINAL_EXAM",
            title="Final",
            max_score=100,
            passing_score=60,
        )
        quiz = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="QUIZ",
            title="Quiz",
            max_score=100,
            passing_score=60,
        )

        # Record results
        assessment_service.record_result(final.id, enrollment.id, score=80)
        assessment_service.record_result(quiz.id, enrollment.id, score=90)

        # Calculate final grade
        result = assessment_service.calculate_final_grade(enrollment.id)
        # 80 * 0.6 + 90 * 0.4 = 48 + 36 = 84
        assert result["final_grade"] == 84.0
        assert result["passed"] is True

    def test_calculate_final_grade_missing_scores(self, db, academy_class, enrollment):
        # Create grading template
        assessment_service.create_grading_template(
            class_id=academy_class.id,
            title="Test",
            components=[
                {"assessment_type": "FINAL_EXAM", "weight": 50},
                {"assessment_type": "MIDTERM", "weight": 50},
            ],
        )

        # Create assessments
        final = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="FINAL_EXAM",
            title="Final",
            max_score=100,
            passing_score=60,
        )
        # Only record final exam result (missing midterm)
        assessment_service.record_result(final.id, enrollment.id, score=80)

        result = assessment_service.calculate_final_grade(enrollment.id)
        # 80 * 0.5 + 0 * 0.5 = 40
        assert result["final_grade"] == 40.0
        assert result["passed"] is False

    def test_calculate_final_grade_multiple_assessments_per_type(
        self, db, academy_class, enrollment
    ):
        assessment_service.create_grading_template(
            class_id=academy_class.id,
            title="Test",
            components=[{"assessment_type": "QUIZ", "weight": 100}],
        )

        quiz1 = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="QUIZ",
            title="Quiz 1",
            max_score=100,
            passing_score=60,
        )
        quiz2 = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="QUIZ",
            title="Quiz 2",
            max_score=100,
            passing_score=60,
        )

        assessment_service.record_result(quiz1.id, enrollment.id, score=80)
        assessment_service.record_result(quiz2.id, enrollment.id, score=100)

        result = assessment_service.calculate_final_grade(enrollment.id)
        # Average of 80 and 100 = 90
        assert result["final_grade"] == 90.0

    def test_calculate_final_grade_no_template(self, db, academy_class, enrollment):
        with pytest.raises(assessment_service.AssessmentError, match="template"):
            assessment_service.calculate_final_grade(enrollment.id)


class TestNegativeMarking:
    """Tests for negative marking calculation."""

    def test_negative_marking_basic(self, db, academy_class, enrollment):
        assessment = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="QUIZ",
            title="MCQ Quiz",
            max_score=100,
            passing_score=40,
            penalty_factor=0.33,
        )

        # 30 correct, 10 wrong: effective = 30 - (10 * 0.33) = 26.7
        result = assessment_service.record_result(
            assessment.id, enrollment.id, score=30, wrong_count=10
        )
        assert float(result.score) == 26.7
        assert float(result.percentage) == 26.7

    def test_negative_marking_score_floors_to_zero(self, db, academy_class, enrollment):
        assessment = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="QUIZ",
            title="MCQ Quiz",
            max_score=100,
            passing_score=40,
            penalty_factor=0.33,
        )

        # 10 correct, 50 wrong: effective = 10 - (50 * 0.33) = negative -> 0
        result = assessment_service.record_result(
            assessment.id, enrollment.id, score=10, wrong_count=50
        )
        assert float(result.score) == 0.0

    def test_negative_marking_zero_penalty(self, db, academy_class, enrollment):
        assessment = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="QUIZ",
            title="Regular Quiz",
            max_score=100,
            passing_score=60,
            penalty_factor=0,
        )

        result = assessment_service.record_result(
            assessment.id, enrollment.id, score=80, wrong_count=5
        )
        # No penalty applied
        assert float(result.score) == 80.0

    def test_negative_marking_no_wrong_count(self, db, academy_class, enrollment):
        assessment = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="QUIZ",
            title="MCQ Quiz",
            max_score=100,
            passing_score=60,
            penalty_factor=0.33,
        )

        # Score only, no wrong_count
        result = assessment_service.record_result(
            assessment.id, enrollment.id, score=80
        )
        assert float(result.score) == 80.0

    def test_negative_marking_wrong_count_validation(
        self, db, academy_class, enrollment
    ):
        assessment = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="QUIZ",
            title="MCQ Quiz",
            max_score=100,
            passing_score=60,
            penalty_factor=0.33,
        )

        with pytest.raises(assessment_service.AssessmentError, match="negative"):
            assessment_service.record_result(
                assessment.id, enrollment.id, score=30, wrong_count=-5
            )


class TestAssessmentPenaltyFactor:
    """Tests for assessment penalty_factor field."""

    def test_create_assessment_with_penalty_factor(self, db, academy_class, admin_user):
        assessment = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="QUIZ",
            title="MCQ Quiz",
            max_score=100,
            passing_score=60,
            penalty_factor=0.33,
            created_by=admin_user.id,
        )
        assert float(assessment.penalty_factor) == 0.33

    def test_create_assessment_invalid_penalty_factor(self, db, academy_class):
        with pytest.raises(assessment_service.AssessmentError, match="between 0 and 1"):
            assessment_service.create_assessment(
                class_id=academy_class.id,
                assessment_type="QUIZ",
                title="Invalid",
                penalty_factor=1.5,
            )


class TestTranscript:
    """Tests for transcript generation."""

    def test_get_transcript_data(self, db, academy_class, enrollment):
        # Create grading template
        assessment_service.create_grading_template(
            class_id=academy_class.id,
            title="Test",
            components=[{"assessment_type": "FINAL_EXAM", "weight": 100}],
        )

        # Create assessment and result
        assessment = assessment_service.create_assessment(
            class_id=academy_class.id,
            assessment_type="FINAL_EXAM",
            title="Final",
            max_score=100,
            passing_score=60,
        )
        assessment_service.record_result(assessment.id, enrollment.id, score=85)

        # Get transcript
        transcript = assessment_service.get_transcript_data(enrollment.id)
        assert transcript["student_name"] == "Ali Rezaei"
        assert transcript["final_grade"] == 85.0
        assert transcript["passed"] is True
        assert len(transcript["results"]) == 1

    def test_get_transcript_data_no_template(self, db, academy_class, enrollment):
        transcript = assessment_service.get_transcript_data(enrollment.id)
        assert transcript["final_grade"] is None


# ---------------------------------------------------------------------------
# Transcript route authorization (IDOR regression coverage)
# ---------------------------------------------------------------------------


class TestTranscriptAuthorization:
    """Route-level tests for GET /assessment/student/<id>/transcript.

    A teacher must only view transcripts for classes they teach; any bare
    TEACHER-role check would let one teacher read every enrollment.
    """

    def _login(self, client, login, password):
        return client.post(
            "/auth/login", data={"login": login, "password": password}
        )

    def _other_teacher_class_enrollment(self, db, course):
        """Create a second teacher, their class, and an enrollment in it."""
        other_teacher = UserModel(login="teacher2")
        other_teacher.set_password("teacherpass2")
        role = RoleModel.query.get("TEACHER")
        if role is None:
            role = RoleModel(name="TEACHER")
            db.session.add(role)
            db.session.flush()
        other_teacher.roles.append(role)
        db.session.add(other_teacher)
        db.session.flush()
        other_class = AcademyClassModel(
            course_id=course.id,
            title="Other Class",
            start_date=date(2026, 1, 1),
            capacity=30,
            num_sessions=10,
            status="ACTIVE",
            teacher_user_id=other_teacher.id,
        )
        db.session.add(other_class)
        db.session.flush()
        other_student = UserModel(login="otherstudent")
        other_student.set_password("otherpass")
        db.session.add(other_student)
        db.session.flush()
        other_enrollment = EnrollmentModel(
            student_user_id=other_student.id,
            class_id=other_class.id,
            status="APPROVED",
        )
        db.session.add(other_enrollment)
        db.session.commit()
        return other_teacher, other_enrollment

    def test_teacher_of_own_class_can_view(
        self, client, db, teacher_user, enrollment
    ):
        self._login(client, "teacher", "teacherpass")
        resp = client.get(f"/assessment/student/{enrollment.id}/transcript")
        assert resp.status_code == 200

    def test_teacher_of_other_class_denied(
        self, client, db, course, teacher_user, student_user
    ):
        _, other_enrollment = self._other_teacher_class_enrollment(db, course)
        self._login(client, "teacher", "teacherpass")
        resp = client.get(
            f"/assessment/student/{other_enrollment.id}/transcript"
        )
        assert resp.status_code == 403

    def test_teacher_without_classes_denied(
        self, client, db, course, enrollment
    ):
        # A teacher assigned to no class must be denied everywhere.
        lonely = UserModel(login="lonelyteacher")
        lonely.set_password("lonelypass")
        role = RoleModel.query.get("TEACHER")
        if role is None:
            role = RoleModel(name="TEACHER")
            db.session.add(role)
            db.session.flush()
        lonely.roles.append(role)
        db.session.add(lonely)
        db.session.commit()
        self._login(client, "lonelyteacher", "lonelypass")
        resp = client.get(f"/assessment/student/{enrollment.id}/transcript")
        assert resp.status_code == 403

    def test_student_owner_can_view(self, client, db, student_user, enrollment):
        self._login(client, "student", "studentpass")
        resp = client.get(f"/assessment/student/{enrollment.id}/transcript")
        assert resp.status_code == 200

    def test_other_student_denied(
        self, client, db, academy_class, enrollment
    ):
        # A different student enrolled in the SAME class still must be denied:
        # ownership is per-enrollment, not per-class.
        other = UserModel(login="studentx")
        other.set_password("studentxpass")
        role = RoleModel.query.get("STUDENT")
        if role is None:
            role = RoleModel(name="STUDENT")
            db.session.add(role)
            db.session.flush()
        other.roles.append(role)
        db.session.add(other)
        db.session.flush()
        db.session.add(
            EnrollmentModel(
                student_user_id=other.id,
                class_id=academy_class.id,
                status="APPROVED",
            )
        )
        db.session.commit()
        self._login(client, "studentx", "studentxpass")
        resp = client.get(f"/assessment/student/{enrollment.id}/transcript")
        assert resp.status_code == 403

    def test_linked_parent_can_view(
        self, client, db, parent_user, student_user, enrollment
    ):
        from app.infrastructure.database.models import ParentProfileModel

        profile = ParentProfileModel(
            user_id=parent_user.id,
            first_name="Parent",
            last_name="One",
            national_id="P1234567890",
            mobile_phone="09120000002",
        )
        db.session.add(profile)
        db.session.flush()
        profile.children.append(student_user.student_profile)
        db.session.commit()
        self._login(client, "parent", "parentpass")
        resp = client.get(f"/assessment/student/{enrollment.id}/transcript")
        assert resp.status_code == 200

    def test_unlinked_parent_denied(
        self, client, db, parent_user, enrollment
    ):
        self._login(client, "parent", "parentpass")
        resp = client.get(f"/assessment/student/{enrollment.id}/transcript")
        assert resp.status_code == 403

    def test_admin_can_view(self, client, db, admin_user, enrollment):
        self._login(client, "admin", "adminpass")
        resp = client.get(f"/assessment/student/{enrollment.id}/transcript")
        assert resp.status_code == 200

    def test_unauthenticated_redirected(self, client, db, enrollment):
        resp = client.get(
            f"/assessment/student/{enrollment.id}/transcript",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]

    def test_nonexistent_enrollment_404(
        self, client, db, admin_user
    ):
        self._login(client, "admin", "adminpass")
        resp = client.get("/assessment/student/999999/transcript")
        assert resp.status_code == 404
