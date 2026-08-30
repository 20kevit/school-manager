"""Tests for Enrollment services."""

from datetime import date, time

import pytest

from app.application.academy.class_service import create_class
from app.application.academy.course_service import create_course
from app.application.enrollment.enrollment_service import (
    EnrollmentError,
    admin_enroll_student,
    approve_enrollment,
    cancel_enrollment,
    count_approved_enrollments,
    get_enrollment,
    list_enrollments_by_class,
    list_enrollments_by_student,
    reject_enrollment,
    request_enrollment,
)
from app.infrastructure.database.models import UserModel


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
        capacity=3,
        schedule=mon_wed_schedule,
    )


class TestEnrollmentCreation:
    """Tests for enrollment creation."""

    def test_request_enrollment(self, db, student_user, academy_class):
        enrollment = request_enrollment(
            student_user_id=student_user.id,
            class_id=academy_class.id,
        )
        assert enrollment.id is not None
        assert enrollment.student_user_id == student_user.id
        assert enrollment.class_id == academy_class.id
        assert enrollment.status == "PENDING"
        assert enrollment.requested_at is not None

    def test_request_enrollment_nonexistent_student_fails(self, db, academy_class):
        with pytest.raises(EnrollmentError, match="Student not found"):
            request_enrollment(student_user_id=9999, class_id=academy_class.id)

    def test_request_enrollment_non_student_fails(self, db, admin_user, academy_class):
        with pytest.raises(EnrollmentError, match="User is not a student"):
            request_enrollment(
                student_user_id=admin_user.id,
                class_id=academy_class.id,
            )

    def test_request_enrollment_nonexistent_class_fails(self, db, student_user):
        with pytest.raises(EnrollmentError, match="Class not found"):
            request_enrollment(
                student_user_id=student_user.id,
                class_id=9999,
            )

    def test_request_enrollment_cancelled_class_fails(
        self, db, student_user, course, mon_wed_schedule
    ):
        cls = create_class(
            course_id=course.id,
            title="Cancelled Class",
            start_date=date(2026, 9, 7),
            schedule=mon_wed_schedule,
        )
        cls.status = "CANCELLED"
        db.session.commit()

        with pytest.raises(EnrollmentError, match="not accepting enrollments"):
            request_enrollment(
                student_user_id=student_user.id,
                class_id=cls.id,
            )

    def test_duplicate_active_enrollment_fails(self, db, student_user, academy_class):
        request_enrollment(
            student_user_id=student_user.id,
            class_id=academy_class.id,
        )
        with pytest.raises(EnrollmentError, match="already enrolled"):
            request_enrollment(
                student_user_id=student_user.id,
                class_id=academy_class.id,
            )


class TestAdminEnrollment:
    """Tests for admin direct enrollment."""

    def test_admin_enroll_student(self, db, student_user, academy_class):
        enrollment = admin_enroll_student(
            student_user_id=student_user.id,
            class_id=academy_class.id,
            auto_approve=True,
        )
        assert enrollment.id is not None
        assert enrollment.status == "APPROVED"
        assert enrollment.approved_at is not None

    def test_admin_enroll_student_pending(self, db, student_user, academy_class):
        enrollment = admin_enroll_student(
            student_user_id=student_user.id,
            class_id=academy_class.id,
            auto_approve=False,
        )
        assert enrollment.status == "PENDING"
        assert enrollment.approved_at is None

    def test_admin_enroll_nonexistent_student_fails(self, db, academy_class):
        with pytest.raises(EnrollmentError, match="Student not found"):
            admin_enroll_student(
                student_user_id=9999,
                class_id=academy_class.id,
            )

    def test_admin_enroll_non_student_fails(self, db, admin_user, academy_class):
        with pytest.raises(EnrollmentError, match="User is not a student"):
            admin_enroll_student(
                student_user_id=admin_user.id,
                class_id=academy_class.id,
            )

    def test_admin_enroll_duplicate_fails(self, db, student_user, academy_class):
        admin_enroll_student(
            student_user_id=student_user.id,
            class_id=academy_class.id,
        )
        with pytest.raises(EnrollmentError, match="already enrolled"):
            admin_enroll_student(
                student_user_id=student_user.id,
                class_id=academy_class.id,
            )


class TestApproval:
    """Tests for enrollment approval."""

    def test_approve_pending_enrollment(self, db, student_user, academy_class):
        enrollment = request_enrollment(
            student_user_id=student_user.id,
            class_id=academy_class.id,
        )
        approved = approve_enrollment(enrollment)
        assert approved.status == "APPROVED"
        assert approved.approved_at is not None

    def test_approve_non_pending_fails(self, db, student_user, academy_class):
        enrollment = request_enrollment(
            student_user_id=student_user.id,
            class_id=academy_class.id,
        )
        approve_enrollment(enrollment)

        with pytest.raises(EnrollmentError, match="Only pending"):
            approve_enrollment(enrollment)

    def test_approve_capacity_check(self, db, student_user, academy_class):
        admin_enroll_student(
            student_user_id=student_user.id,
            class_id=academy_class.id,
            auto_approve=True,
        )

        from app.infrastructure.database.models import RoleModel, StudentProfileModel

        users = []
        for i in range(2):
            user = UserModel(login=f"student{i + 2}")
            user.set_password("pass123")
            role = RoleModel.query.filter_by(name="STUDENT").first()
            user.roles.append(role)
            db.session.add(user)
            db.session.flush()

            profile = StudentProfileModel(
                user_id=user.id,
                first_name=f"Student{i + 2}",
                last_name="Test",
                national_id=f"223456789{i}",
                mobile_phone=f"0912123456{i}",
                birth_date=date(2000, 1, 15),
                gender="MALE",
            )
            db.session.add(profile)
            db.session.flush()

            admin_enroll_student(
                student_user_id=user.id,
                class_id=academy_class.id,
                auto_approve=True,
            )
            users.append(user)

        assert count_approved_enrollments(academy_class.id) == 3

        user3 = UserModel(login="student5")
        user3.set_password("pass123")
        role = RoleModel.query.filter_by(name="STUDENT").first()
        user3.roles.append(role)
        db.session.add(user3)
        db.session.flush()

        profile3 = StudentProfileModel(
            user_id=user3.id,
            first_name="Student5",
            last_name="Test",
            national_id="2234567892",
            mobile_phone="09121234562",
            birth_date=date(2000, 1, 15),
            gender="MALE",
        )
        db.session.add(profile3)
        db.session.flush()

        enrollment = admin_enroll_student(
            student_user_id=user3.id,
            class_id=academy_class.id,
            auto_approve=False,
        )

        with pytest.raises(EnrollmentError, match="full capacity"):
            approve_enrollment(enrollment)


class TestRejection:
    """Tests for enrollment rejection."""

    def test_reject_pending_enrollment(self, db, student_user, academy_class):
        enrollment = request_enrollment(
            student_user_id=student_user.id,
            class_id=academy_class.id,
        )
        rejected = reject_enrollment(enrollment)
        assert rejected.status == "REJECTED"
        assert rejected.rejected_at is not None

    def test_reject_non_pending_fails(self, db, student_user, academy_class):
        enrollment = request_enrollment(
            student_user_id=student_user.id,
            class_id=academy_class.id,
        )
        reject_enrollment(enrollment)

        with pytest.raises(EnrollmentError, match="Only pending"):
            reject_enrollment(enrollment)

    def test_rejected_enrollment_preserved(self, db, student_user, academy_class):
        enrollment = request_enrollment(
            student_user_id=student_user.id,
            class_id=academy_class.id,
        )
        reject_enrollment(enrollment)

        from app.infrastructure.database.models import EnrollmentModel

        saved = EnrollmentModel.query.get(enrollment.id)
        assert saved is not None
        assert saved.status == "REJECTED"


class TestCancellation:
    """Tests for enrollment cancellation."""

    def test_cancel_pending_enrollment(self, db, student_user, academy_class):
        enrollment = request_enrollment(
            student_user_id=student_user.id,
            class_id=academy_class.id,
        )
        cancelled = cancel_enrollment(enrollment)
        assert cancelled.status == "CANCELLED"
        assert cancelled.cancelled_at is not None

    def test_cancel_approved_enrollment(self, db, student_user, academy_class):
        enrollment = admin_enroll_student(
            student_user_id=student_user.id,
            class_id=academy_class.id,
            auto_approve=True,
        )
        cancelled = cancel_enrollment(enrollment)
        assert cancelled.status == "CANCELLED"
        assert cancelled.cancelled_at is not None

    def test_cancel_rejected_fails(self, db, student_user, academy_class):
        enrollment = request_enrollment(
            student_user_id=student_user.id,
            class_id=academy_class.id,
        )
        reject_enrollment(enrollment)

        with pytest.raises(EnrollmentError, match="Only pending or approved"):
            cancel_enrollment(enrollment)

    def test_cancelled_enrollment_preserved(self, db, student_user, academy_class):
        enrollment = admin_enroll_student(
            student_user_id=student_user.id,
            class_id=academy_class.id,
            auto_approve=True,
        )
        cancel_enrollment(enrollment)

        from app.infrastructure.database.models import EnrollmentModel

        saved = EnrollmentModel.query.get(enrollment.id)
        assert saved is not None
        assert saved.status == "CANCELLED"


class TestCapacity:
    """Tests for capacity enforcement."""

    def test_capacity_check(self, db, student_user):
        from datetime import time as time_type

        from app.infrastructure.database.models import RoleModel, StudentProfileModel

        schedule = [
            {
                "weekday": "MONDAY",
                "start_time": time_type(17, 0),
                "end_time": time_type(19, 0),
            },
        ]

        cls = create_class(
            course_id=create_course(title="Cap Course", num_sessions=1).id,
            title="Capacity Test",
            start_date=date(2026, 9, 7),
            capacity=2,
            schedule=schedule,
        )

        admin_enroll_student(
            student_user_id=student_user.id,
            class_id=cls.id,
            auto_approve=True,
        )

        user2 = UserModel(login="cap_student_2")
        user2.set_password("pass123")
        role = RoleModel.query.filter_by(name="STUDENT").first()
        user2.roles.append(role)
        db.session.add(user2)
        db.session.flush()

        profile2 = StudentProfileModel(
            user_id=user2.id,
            first_name="Cap2",
            last_name="Test",
            national_id="4876543210",
            mobile_phone="09129876540",
            birth_date=date(2000, 1, 15),
            gender="MALE",
        )
        db.session.add(profile2)
        db.session.flush()

        admin_enroll_student(
            student_user_id=user2.id,
            class_id=cls.id,
            auto_approve=True,
        )

        assert count_approved_enrollments(cls.id) == 2

        user3 = UserModel(login="cap_student_3")
        user3.set_password("pass123")
        user3.roles.append(role)
        db.session.add(user3)
        db.session.flush()

        profile3 = StudentProfileModel(
            user_id=user3.id,
            first_name="Cap3",
            last_name="Test",
            national_id="5876543210",
            mobile_phone="09129876541",
            birth_date=date(2000, 1, 15),
            gender="MALE",
        )
        db.session.add(profile3)
        db.session.flush()

        enrollment3 = admin_enroll_student(
            student_user_id=user3.id,
            class_id=cls.id,
            auto_approve=False,
        )

        with pytest.raises(EnrollmentError, match="full capacity"):
            approve_enrollment(enrollment3)


class TestQueries:
    """Tests for enrollment queries."""

    def test_list_by_student(self, db, student_user, academy_class):
        request_enrollment(
            student_user_id=student_user.id,
            class_id=academy_class.id,
        )
        enrollments = list_enrollments_by_student(student_user.id)
        assert len(enrollments) == 1
        assert enrollments[0].student_user_id == student_user.id

    def test_list_by_class(self, db, student_user, academy_class):
        request_enrollment(
            student_user_id=student_user.id,
            class_id=academy_class.id,
        )
        enrollments = list_enrollments_by_class(academy_class.id)
        assert len(enrollments) == 1
        assert enrollments[0].class_id == academy_class.id

    def test_get_enrollment(self, db, student_user, academy_class):
        enrollment = request_enrollment(
            student_user_id=student_user.id,
            class_id=academy_class.id,
        )
        fetched = get_enrollment(enrollment.id)
        assert fetched is not None
        assert fetched.id == enrollment.id

    def test_get_nonexistent_enrollment(self, db):
        assert get_enrollment(9999) is None
