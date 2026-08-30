"""Tests for Activity services and routes."""

from datetime import date, datetime, time, timedelta

import pytest

from app.application.academy.class_service import create_class
from app.application.academy.course_service import create_course
from app.application.activity.activity_service import (
    ActivityError,
    compute_activity_submissions_summary,
    copy_course_activities_to_class,
    create_activity,
    deactivate_activity,
    get_all_submissions_for_activity,
    get_latest_submission,
    get_student_enrolled_classes,
    get_submission_history,
    grade_submission,
    is_student_enrolled,
    is_teacher_of_class,
    list_activities_by_class,
    list_activities_by_class_all,
    list_activities_by_course,
    list_activities_by_session,
    return_submission,
    submit_activity,
    update_activity,
    validate_file,
)
from app.application.enrollment.enrollment_service import admin_enroll_student
from app.infrastructure.database.models import (
    ActivitySubmissionModel,
    RoleModel,
    StudentProfileModel,
    UserModel,
)


@pytest.fixture
def course(db):
    return create_course(
        title="Python Course",
        description="Intro to Python",
        num_sessions=8,
    )


@pytest.fixture
def mon_wed_schedule():
    return [
        {"weekday": "MONDAY", "start_time": time(17, 0), "end_time": time(19, 0)},
        {"weekday": "WEDNESDAY", "start_time": time(18, 0), "end_time": time(20, 0)},
    ]


@pytest.fixture
def academy_class(db, course, mon_wed_schedule):
    return create_class(
        course_id=course.id,
        title="Python Group A",
        start_date=date(2026, 9, 7),
        capacity=5,
        schedule=mon_wed_schedule,
    )


@pytest.fixture
def session(db, academy_class):
    from app.infrastructure.database.models import SessionModel

    return SessionModel.query.filter_by(class_id=academy_class.id).first()


@pytest.fixture
def enrollment(db, student_user, academy_class):
    return admin_enroll_student(
        student_user_id=student_user.id,
        class_id=academy_class.id,
        auto_approve=True,
    )


@pytest.fixture
def second_student(db):
    user = UserModel(login="student2")
    user.set_password("pass123")
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
        national_id="9876543210",
        mobile_phone="09129876543",
        birth_date=date(2001, 5, 10),
        gender="FEMALE",
    )
    db.session.add(profile)
    db.session.commit()
    return user


# ---------------------------------------------------------------------------
# Activity creation tests
# ---------------------------------------------------------------------------


class TestActivityCreation:
    def test_create_homework(self, db, academy_class):
        activity = create_activity(
            activity_type="HOMEWORK",
            title="Chapter 3 Homework",
            class_id=academy_class.id,
        )
        assert activity.id is not None
        assert activity.type == "HOMEWORK"
        assert activity.title == "Chapter 3 Homework"
        assert activity.is_active is True
        assert activity.max_score == 100

    def test_create_with_description(self, db, academy_class):
        activity = create_activity(
            activity_type="HOMEWORK",
            title="HW1",
            description="Complete exercises 1-5",
            class_id=academy_class.id,
        )
        assert activity.description == "Complete exercises 1-5"

    def test_create_optional_activity(self, db, academy_class):
        activity = create_activity(
            activity_type="PRACTICE",
            title="Extra Practice",
            requirement="OPTIONAL",
            class_id=academy_class.id,
        )
        assert activity.requirement == "OPTIONAL"

    def test_create_with_deadline(self, db, academy_class):
        deadline = datetime(2026, 9, 15, 23, 59)
        activity = create_activity(
            activity_type="HOMEWORK",
            title="HW1",
            deadline=deadline,
            class_id=academy_class.id,
        )
        assert activity.deadline == deadline

    def test_create_without_deadline(self, db, academy_class):
        activity = create_activity(
            activity_type="HOMEWORK",
            title="HW1",
            class_id=academy_class.id,
        )
        assert activity.deadline is None

    def test_create_with_custom_max_score(self, db, academy_class):
        activity = create_activity(
            activity_type="HOMEWORK",
            title="HW1",
            max_score=50.0,
            class_id=academy_class.id,
        )
        assert float(activity.max_score) == 50.0

    def test_create_with_sort_order(self, db, academy_class):
        activity = create_activity(
            activity_type="HOMEWORK",
            title="HW1",
            sort_order=3,
            class_id=academy_class.id,
        )
        assert activity.sort_order == 3

    def test_invalid_type_raises_error(self, db, academy_class):
        with pytest.raises(ActivityError, match="Invalid activity type"):
            create_activity(
                activity_type="INVALID",
                title="Test",
                class_id=academy_class.id,
            )

    def test_empty_title_raises_error(self, db, academy_class):
        with pytest.raises(ActivityError, match="title is required"):
            create_activity(
                activity_type="HOMEWORK",
                title="",
                class_id=academy_class.id,
            )

    def test_negative_max_score_raises_error(self, db, academy_class):
        with pytest.raises(ActivityError, match="non-negative"):
            create_activity(
                activity_type="HOMEWORK",
                title="HW1",
                max_score=-10,
                class_id=academy_class.id,
            )


# ---------------------------------------------------------------------------
# Activity type tests
# ---------------------------------------------------------------------------


class TestActivityTypes:
    def test_homework_type(self, db, academy_class):
        a = create_activity("HOMEWORK", "HW", class_id=academy_class.id)
        assert a.type == "HOMEWORK"

    def test_project_type(self, db, academy_class):
        a = create_activity("PROJECT", "Project", class_id=academy_class.id)
        assert a.type == "PROJECT"

    def test_practice_type(self, db, academy_class):
        a = create_activity("PRACTICE", "Practice", class_id=academy_class.id)
        assert a.type == "PRACTICE"

    def test_quiz_type(self, db, academy_class):
        a = create_activity("QUIZ", "Quiz", class_id=academy_class.id)
        assert a.type == "QUIZ"

    def test_exam_type(self, db, academy_class):
        a = create_activity("EXAM", "Exam", class_id=academy_class.id)
        assert a.type == "EXAM"


# ---------------------------------------------------------------------------
# Activity relationships tests
# ---------------------------------------------------------------------------


class TestActivityRelationships:
    def test_course_level_activity(self, db, course):
        activity = create_activity("HOMEWORK", "Course HW", course_id=course.id)
        assert activity.course_id == course.id
        assert activity.class_id is None
        assert activity.session_id is None

    def test_class_level_activity(self, db, academy_class):
        activity = create_activity("HOMEWORK", "Class HW", class_id=academy_class.id)
        assert activity.class_id == academy_class.id
        assert activity.course_id is None
        assert activity.session_id is None

    def test_session_level_activity(self, db, academy_class, session):
        activity = create_activity(
            "HOMEWORK",
            "Session HW",
            class_id=academy_class.id,
            session_id=session.id,
        )
        assert activity.session_id == session.id
        assert activity.class_id == academy_class.id

    def test_session_auto_sets_class(self, db, academy_class, session):
        activity = create_activity(
            "HOMEWORK",
            "Session HW",
            session_id=session.id,
        )
        assert activity.class_id == academy_class.id

    def test_session_wrong_class_raises_error(self, db, session):
        with pytest.raises(ActivityError, match="does not belong"):
            create_activity(
                "HOMEWORK",
                "HW",
                class_id=9999,
                session_id=session.id,
            )

    def test_multiple_activities_per_session(self, db, academy_class, session):
        create_activity(
            "HOMEWORK",
            "HW A",
            class_id=academy_class.id,
            session_id=session.id,
            sort_order=1,
        )
        create_activity(
            "HOMEWORK",
            "HW B",
            class_id=academy_class.id,
            session_id=session.id,
            sort_order=2,
        )
        activities = list_activities_by_session(session.id)
        assert len(activities) == 2

    def test_independent_activity_no_session(self, db, academy_class):
        activity = create_activity(
            "PROJECT",
            "Final Project",
            class_id=academy_class.id,
        )
        assert activity.session_id is None
        assert activity.class_id == academy_class.id


# ---------------------------------------------------------------------------
# Activity update and deactivation tests
# ---------------------------------------------------------------------------


class TestActivityUpdate:
    def test_update_title(self, db, academy_class):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        update_activity(activity, title="Updated HW")
        assert activity.title == "Updated HW"

    def test_update_description(self, db, academy_class):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        update_activity(activity, description="New description")
        assert activity.description == "New description"

    def test_update_requirement(self, db, academy_class):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        update_activity(activity, requirement="OPTIONAL")
        assert activity.requirement == "OPTIONAL"

    def test_update_max_score(self, db, academy_class):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        update_activity(activity, max_score=200.0)
        assert float(activity.max_score) == 200.0

    def test_update_empty_title_raises_error(self, db, academy_class):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        with pytest.raises(ActivityError, match="cannot be empty"):
            update_activity(activity, title="")

    def test_deactivate(self, db, academy_class):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        assert activity.is_active is True
        deactivate_activity(activity)
        assert activity.is_active is False

    def test_deactivated_activity_not_in_active_list(self, db, academy_class):
        create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        a2 = create_activity("HOMEWORK", "HW2", class_id=academy_class.id)
        deactivate_activity(a2)
        active = list_activities_by_class(academy_class.id)
        assert len(active) == 1
        assert active[0].title == "HW1"

    def test_deactivated_in_all_list(self, db, academy_class):
        create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        a2 = create_activity("HOMEWORK", "HW2", class_id=academy_class.id)
        deactivate_activity(a2)
        all_activities = list_activities_by_class_all(academy_class.id)
        assert len(all_activities) == 2


# ---------------------------------------------------------------------------
# Course → Class activity copying tests
# ---------------------------------------------------------------------------


class TestCourseClassCopying:
    def test_copy_activities(self, db, course, academy_class):
        create_activity("HOMEWORK", "Course HW1", course_id=course.id, sort_order=1)
        create_activity("HOMEWORK", "Course HW2", course_id=course.id, sort_order=2)

        copied = copy_course_activities_to_class(course.id, academy_class.id)
        assert len(copied) == 2

        class_activities = list_activities_by_class(academy_class.id)
        assert len(class_activities) == 2
        assert class_activities[0].class_id == academy_class.id
        assert class_activities[0].course_id is None

    def test_copy_preserves_course_defaults(self, db, course, academy_class):
        create_activity("HOMEWORK", "Course HW1", course_id=course.id)
        copy_course_activities_to_class(course.id, academy_class.id)

        course_activities = list_activities_by_course(course.id)
        assert len(course_activities) == 1
        assert course_activities[0].course_id == course.id

    def test_class_customization_does_not_modify_course(
        self, db, course, academy_class
    ):
        create_activity("HOMEWORK", "Course HW1", course_id=course.id)
        copied = copy_course_activities_to_class(course.id, academy_class.id)

        update_activity(copied[0], title="Modified in Class")

        course_activities = list_activities_by_course(course.id)
        assert course_activities[0].title == "Course HW1"

    def test_copy_empty_course(self, db, course, academy_class):
        copied = copy_course_activities_to_class(course.id, academy_class.id)
        assert len(copied) == 0


# ---------------------------------------------------------------------------
# Submission tests
# ---------------------------------------------------------------------------


class TestSubmission:
    def test_submit_activity(self, db, academy_class, enrollment):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        submission = submit_activity(
            activity.id, enrollment.student_user_id, "My answer"
        )
        assert submission.id is not None
        assert submission.text_content == "My answer"
        assert submission.version == 1
        assert submission.status == "SUBMITTED"

    def test_submit_late_activity(self, db, academy_class, enrollment):
        deadline = datetime.now() - timedelta(hours=1)
        activity = create_activity(
            "HOMEWORK", "HW1", class_id=academy_class.id, deadline=deadline
        )
        submission = submit_activity(activity.id, enrollment.student_user_id)
        assert submission.status == "LATE"

    def test_submit_no_deadline_not_late(self, db, academy_class, enrollment):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        submission = submit_activity(activity.id, enrollment.student_user_id)
        assert submission.status == "SUBMITTED"

    def test_resubmit_creates_new_version(self, db, academy_class, enrollment):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        s1 = submit_activity(activity.id, enrollment.student_user_id, "Version 1")
        s2 = submit_activity(activity.id, enrollment.student_user_id, "Version 2")
        assert s1.version == 1
        assert s2.version == 2
        assert s1.id != s2.id

    def test_submission_history_preserved(self, db, academy_class, enrollment):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        submit_activity(activity.id, enrollment.student_user_id, "V1")
        submit_activity(activity.id, enrollment.student_user_id, "V2")
        submit_activity(activity.id, enrollment.student_user_id, "V3")

        history = get_submission_history(activity.id, enrollment.student_user_id)
        assert len(history) == 3
        assert [h.version for h in history] == [1, 2, 3]

    def test_latest_submission(self, db, academy_class, enrollment):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        submit_activity(activity.id, enrollment.student_user_id, "V1")
        submit_activity(activity.id, enrollment.student_user_id, "V2")

        latest = get_latest_submission(activity.id, enrollment.student_user_id)
        assert latest.version == 2
        assert latest.text_content == "V2"

    def test_submit_inactive_activity_raises_error(self, db, academy_class, enrollment):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        deactivate_activity(activity)
        with pytest.raises(ActivityError, match="no longer active"):
            submit_activity(activity.id, enrollment.student_user_id)

    def test_submit_not_enrolled_raises_error(self, db, academy_class, student_user):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        with pytest.raises(ActivityError, match="not enrolled"):
            submit_activity(activity.id, student_user.id)

    def test_submit_not_approved_enrollment_raises_error(
        self, db, academy_class, student_user
    ):
        admin_enroll_student(
            student_user_id=student_user.id,
            class_id=academy_class.id,
            auto_approve=False,
        )
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        with pytest.raises(ActivityError, match="not enrolled"):
            submit_activity(activity.id, student_user.id)


# ---------------------------------------------------------------------------
# Grading tests
# ---------------------------------------------------------------------------


class TestGrading:
    def test_grade_submission(self, db, academy_class, enrollment):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        submission = submit_activity(activity.id, enrollment.student_user_id)
        graded = grade_submission(submission, 85.0, "Good work", graded_by=1)
        assert float(graded.score) == 85.0
        assert graded.feedback == "Good work"
        assert graded.status == "GRADED"
        assert graded.graded_at is not None
        assert graded.graded_by == 1

    def test_grade_update(self, db, academy_class, enrollment):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        submission = submit_activity(activity.id, enrollment.student_user_id)
        grade_submission(submission, 70.0, "First grade")
        grade_submission(submission, 90.0, "Updated grade")
        assert float(submission.score) == 90.0
        assert submission.feedback == "Updated grade"

    def test_grade_exceeds_max_score_raises_error(self, db, academy_class, enrollment):
        activity = create_activity(
            "HOMEWORK", "HW1", class_id=academy_class.id, max_score=100
        )
        submission = submit_activity(activity.id, enrollment.student_user_id)
        with pytest.raises(ActivityError, match="cannot exceed"):
            grade_submission(submission, 150.0)

    def test_grade_negative_score_raises_error(self, db, academy_class, enrollment):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        submission = submit_activity(activity.id, enrollment.student_user_id)
        with pytest.raises(ActivityError, match="cannot be negative"):
            grade_submission(submission, -10.0)

    def test_decimal_score(self, db, academy_class, enrollment):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        submission = submit_activity(activity.id, enrollment.student_user_id)
        graded = grade_submission(submission, 87.5)
        assert float(graded.score) == 87.5


# ---------------------------------------------------------------------------
# Return and resubmission workflow tests
# ---------------------------------------------------------------------------


class TestReturnResubmission:
    def test_return_submission(self, db, academy_class, enrollment):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        submission = submit_activity(activity.id, enrollment.student_user_id)
        returned = return_submission(submission, "Please fix exercises 2 and 3")
        assert returned.status == "RETURNED"
        assert returned.feedback == "Please fix exercises 2 and 3"

    def test_resubmit_after_return(self, db, academy_class, enrollment):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        s1 = submit_activity(activity.id, enrollment.student_user_id, "V1")
        grade_submission(s1, 60.0, "Needs improvement")
        return_submission(s1, "Fix and resubmit")

        s2 = submit_activity(activity.id, enrollment.student_user_id, "V2")
        assert s2.version == 2
        assert s2.status == "SUBMITTED"

        history = get_submission_history(activity.id, enrollment.student_user_id)
        assert len(history) == 2
        assert history[0].status == "RETURNED"
        assert history[1].status == "SUBMITTED"

    def test_workflow_submitted_returned_resubmitted_graded(
        self, db, academy_class, enrollment
    ):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)

        s1 = submit_activity(activity.id, enrollment.student_user_id, "V1")
        assert s1.status == "SUBMITTED"

        return_submission(s1, "Fix it")
        assert s1.status == "RETURNED"

        s2 = submit_activity(activity.id, enrollment.student_user_id, "V2")
        assert s2.status == "SUBMITTED"

        grade_submission(s2, 95.0, "Excellent")
        assert s2.status == "GRADED"


# ---------------------------------------------------------------------------
# Query tests
# ---------------------------------------------------------------------------


class TestQueries:
    def test_list_by_class(self, db, academy_class):
        create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        create_activity("HOMEWORK", "HW2", class_id=academy_class.id)
        activities = list_activities_by_class(academy_class.id)
        assert len(activities) == 2

    def test_list_by_session(self, db, academy_class, session):
        create_activity(
            "HOMEWORK", "HW1", class_id=academy_class.id, session_id=session.id
        )
        create_activity(
            "HOMEWORK", "HW2", class_id=academy_class.id, session_id=session.id
        )
        activities = list_activities_by_session(session.id)
        assert len(activities) == 2

    def test_list_by_course(self, db, course):
        create_activity("HOMEWORK", "HW1", course_id=course.id)
        activities = list_activities_by_course(course.id)
        assert len(activities) == 1

    def test_get_student_enrolled_classes(
        self, db, student_user, academy_class, enrollment
    ):
        classes = get_student_enrolled_classes(student_user.id)
        assert len(classes) == 1
        assert classes[0].id == academy_class.id

    def test_is_student_enrolled(self, db, student_user, academy_class, enrollment):
        assert is_student_enrolled(student_user.id, academy_class.id) is True

    def test_is_student_not_enrolled(self, db, student_user):
        assert is_student_enrolled(student_user.id, 9999) is False

    def test_is_teacher_of_class(self, db, teacher_user, academy_class):

        academy_class.teacher_user_id = teacher_user.id
        db.session.commit()
        assert is_teacher_of_class(teacher_user.id, academy_class.id) is True

    def test_is_not_teacher_of_class(self, db, teacher_user, academy_class):
        assert is_teacher_of_class(teacher_user.id, academy_class.id) is False

    def test_get_all_submissions_for_activity(self, db, academy_class, enrollment):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        submit_activity(activity.id, enrollment.student_user_id, "Answer")
        submissions = get_all_submissions_for_activity(activity.id)
        assert len(submissions) == 1

    def test_compute_summary(self, db, academy_class, enrollment):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        submit_activity(activity.id, enrollment.student_user_id)
        summary = compute_activity_submissions_summary(activity.id)
        assert summary["total"] == 1
        assert summary["submitted"] == 1
        assert summary["not_submitted"] == 0


# ---------------------------------------------------------------------------
# File validation tests
# ---------------------------------------------------------------------------


class TestFileValidation:
    def test_valid_pdf(self):
        validate_file("homework.pdf", 1024, "application/pdf")

    def test_valid_docx(self):
        validate_file(
            "report.docx",
            2048,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def test_valid_png(self):
        validate_file("image.png", 4096, "image/png")

    def test_valid_zip(self):
        validate_file("archive.zip", 8192, "application/zip")

    def test_invalid_extension(self):
        with pytest.raises(ActivityError, match="not allowed"):
            validate_file("script.exe", 1024, "application/octet-stream")

    def test_oversized_file(self):
        with pytest.raises(ActivityError, match="exceeds maximum"):
            validate_file("big.pdf", 6 * 1024 * 1024, "application/pdf")

    def test_invalid_mime_type(self):
        with pytest.raises(ActivityError, match="not allowed"):
            validate_file("file.pdf", 1024, "text/html")


# ---------------------------------------------------------------------------
# Domain entity tests
# ---------------------------------------------------------------------------


class TestDomainEntities:
    def test_activity_entity(self):
        from app.domain.activity import Activity, ActivityRequirement, ActivityType

        a = Activity(
            id=1,
            activity_type=ActivityType.HOMEWORK,
            title="Test",
            requirement=ActivityRequirement.REQUIRED,
        )
        assert a.activity_type == ActivityType.HOMEWORK
        a.deactivate()
        assert a.is_active is False

    def test_submission_entity(self):
        from app.domain.activity import SubmissionStatus
        from app.domain.submission import ActivitySubmission

        s = ActivitySubmission(
            id=1,
            activity_id=1,
            student_user_id=1,
            enrollment_id=1,
            status=SubmissionStatus.SUBMITTED,
            version=1,
        )
        assert s.version == 1
        assert s.status == SubmissionStatus.SUBMITTED


# ---------------------------------------------------------------------------
# Enrollment integration tests
# ---------------------------------------------------------------------------


class TestEnrollmentIntegration:
    def test_enrolled_student_can_submit(self, db, academy_class, enrollment):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        submission = submit_activity(activity.id, enrollment.student_user_id)
        assert submission.enrollment_id == enrollment.id

    def test_cancelled_enrollment_cannot_submit(self, db, academy_class, student_user):
        from app.application.enrollment.enrollment_service import cancel_enrollment

        enrollment = admin_enroll_student(
            student_user_id=student_user.id,
            class_id=academy_class.id,
            auto_approve=True,
        )
        cancel_enrollment(enrollment)

        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        with pytest.raises(ActivityError, match="not enrolled"):
            submit_activity(activity.id, student_user.id)


# ---------------------------------------------------------------------------
# History preservation tests
# ---------------------------------------------------------------------------


class TestHistoryPreservation:
    def test_deactivate_activity_preserves_submissions(
        self, db, academy_class, enrollment
    ):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        submit_activity(activity.id, enrollment.student_user_id, "Answer")
        deactivate_activity(activity)

        submissions = get_all_submissions_for_activity(activity.id)
        assert len(submissions) == 1

    def test_previous_submissions_not_overwritten(self, db, academy_class, enrollment):
        activity = create_activity("HOMEWORK", "HW1", class_id=academy_class.id)
        s1 = submit_activity(activity.id, enrollment.student_user_id, "V1")
        s2 = submit_activity(activity.id, enrollment.student_user_id, "V2")

        s1_check = ActivitySubmissionModel.query.get(s1.id)
        assert s1_check.text_content == "V1"

        s2_check = ActivitySubmissionModel.query.get(s2.id)
        assert s2_check.text_content == "V2"
