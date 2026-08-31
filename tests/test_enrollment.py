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
    get_schedule_conflict_details,
    has_schedule_conflict,
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


class TestAgeEligibility:
    """Tests for age eligibility checks during enrollment."""

    def test_underage_student_rejected(self, db):
        from datetime import date as date_type

        young_user = UserModel(login="young")
        young_user.set_password("pass123")
        from app.infrastructure.database.models import RoleModel, StudentProfileModel

        role = RoleModel(name="STUDENT")
        db.session.add(role)
        db.session.flush()
        young_user.roles.append(role)
        db.session.add(young_user)
        db.session.flush()

        profile = StudentProfileModel(
            user_id=young_user.id,
            first_name="Young",
            last_name="Student",
            national_id="1111111111",
            mobile_phone="09111111111",
            birth_date=date_type(2018, 1, 1),  # 8 years old
            gender="MALE",
        )
        db.session.add(profile)
        db.session.flush()

        restrictive_course = create_course(
            title="Adults Only", min_age=18, num_sessions=4
        )
        cls = create_class(
            course_id=restrictive_course.id,
            title="Adult Class",
            start_date=date_type(2026, 9, 1),
            schedule=[
                {
                    "weekday": "SATURDAY",
                    "start_time": time(10, 0),
                    "end_time": time(12, 0),
                }
            ],
        )

        with pytest.raises(EnrollmentError, match="under the minimum age"):
            request_enrollment(young_user.id, cls.id)

    def test_overage_student_rejected(self, db):
        from datetime import date as date_type

        old_user = UserModel(login="oldstudent")
        old_user.set_password("pass123")
        from app.infrastructure.database.models import RoleModel, StudentProfileModel

        role = RoleModel(name="STUDENT")
        db.session.add(role)
        db.session.flush()
        old_user.roles.append(role)
        db.session.add(old_user)
        db.session.flush()

        profile = StudentProfileModel(
            user_id=old_user.id,
            first_name="Old",
            last_name="Student",
            national_id="2222222222",
            mobile_phone="09222222222",
            birth_date=date_type(2000, 1, 1),  # 26 years old
            gender="MALE",
        )
        db.session.add(profile)
        db.session.flush()

        kids_course = create_course(title="Kids Only", max_age=10, num_sessions=4)
        cls = create_class(
            course_id=kids_course.id,
            title="Kids Class",
            start_date=date_type(2026, 9, 1),
            schedule=[
                {
                    "weekday": "SATURDAY",
                    "start_time": time(10, 0),
                    "end_time": time(12, 0),
                }
            ],
        )

        with pytest.raises(EnrollmentError, match="exceeds the maximum age"):
            request_enrollment(old_user.id, cls.id)

    def test_eligible_student_enrolled(self, db, student_user):
        from datetime import date as date_type

        eligible_course = create_course(title="All Ages", num_sessions=4)
        cls = create_class(
            course_id=eligible_course.id,
            title="Open Class",
            start_date=date_type(2026, 9, 1),
            schedule=[
                {
                    "weekday": "SATURDAY",
                    "start_time": time(10, 0),
                    "end_time": time(12, 0),
                }
            ],
        )

        enrollment = request_enrollment(student_user.id, cls.id)
        assert enrollment.status == "PENDING"


class TestScheduleConflictDetection:
    """Tests for has_schedule_conflict service."""

    def _make_class_with_schedule(self, db, course, teacher, weekday, start_h, end_h):
        """Helper to create a class with a single schedule entry."""
        cls = create_class(
            course_id=course.id,
            title=f"Class {weekday} {start_h}-{end_h}",
            start_date=date(2026, 9, 7),
            capacity=20,
            num_sessions=5,
            schedule=[
                {
                    "weekday": weekday,
                    "start_time": time(start_h, 0),
                    "end_time": time(end_h, 0),
                }
            ],
        )
        if teacher:
            from app.infrastructure.database.models import AcademyClassModel

            AcademyClassModel.query.get(cls.id).teacher_user_id = teacher.id
            db.session.commit()
        return cls

    def test_no_conflict_different_days(self, db, student_user, course, teacher_user):
        cls_a = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 8, 10
        )
        cls_b = self._make_class_with_schedule(
            db, course, teacher_user, "MONDAY", 8, 10
        )

        admin_enroll_student(student_user.id, cls_a.id, auto_approve=True)
        conflicts = has_schedule_conflict(student_user.id, cls_b.id)
        assert conflicts == []

    def test_no_conflict_same_day_different_time(
        self, db, student_user, course, teacher_user
    ):
        cls_a = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 8, 10
        )
        cls_b = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 10, 12
        )

        admin_enroll_student(student_user.id, cls_a.id, auto_approve=True)
        conflicts = has_schedule_conflict(student_user.id, cls_b.id)
        assert conflicts == []

    def test_conflict_same_day_overlapping_time(
        self, db, student_user, course, teacher_user
    ):
        cls_a = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 8, 10
        )
        cls_b = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 9, 11
        )

        admin_enroll_student(student_user.id, cls_a.id, auto_approve=True)
        conflicts = has_schedule_conflict(student_user.id, cls_b.id)
        assert len(conflicts) == 1
        assert conflicts[0].id == cls_a.id

    def test_conflict_exact_same_time(self, db, student_user, course, teacher_user):
        cls_a = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 8, 10
        )
        cls_b = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 8, 10
        )

        admin_enroll_student(student_user.id, cls_a.id, auto_approve=True)
        conflicts = has_schedule_conflict(student_user.id, cls_b.id)
        assert len(conflicts) == 1

    def test_no_conflict_contiguous_times(self, db, student_user, course, teacher_user):
        cls_a = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 8, 10
        )
        cls_b = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 10, 12
        )

        admin_enroll_student(student_user.id, cls_a.id, auto_approve=True)
        conflicts = has_schedule_conflict(student_user.id, cls_b.id)
        assert conflicts == []

    def test_conflict_partial_overlap(self, db, student_user, course, teacher_user):
        cls_a = self._make_class_with_schedule(
            db, course, teacher_user, "WEDNESDAY", 14, 16
        )
        cls_b = self._make_class_with_schedule(
            db, course, teacher_user, "WEDNESDAY", 15, 17
        )

        admin_enroll_student(student_user.id, cls_a.id, auto_approve=True)
        conflicts = has_schedule_conflict(student_user.id, cls_b.id)
        assert len(conflicts) == 1

    def test_conflict_multiple_existing_classes(
        self, db, student_user, course, teacher_user
    ):
        cls_a = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 8, 10
        )
        cls_b = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 10, 12
        )
        cls_c = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 9, 11
        )

        admin_enroll_student(student_user.id, cls_a.id, auto_approve=True)
        admin_enroll_student(student_user.id, cls_b.id, auto_approve=True)

        conflicts = has_schedule_conflict(student_user.id, cls_c.id)
        assert len(conflicts) == 2
        conflict_ids = {c.id for c in conflicts}
        assert cls_a.id in conflict_ids
        assert cls_b.id in conflict_ids

    def test_no_conflict_no_enrollments(self, db, student_user, course, teacher_user):
        cls = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 8, 10
        )
        conflicts = has_schedule_conflict(student_user.id, cls.id)
        assert conflicts == []

    def test_no_conflict_pending_enrollment_considered(
        self, db, student_user, course, teacher_user
    ):
        cls_a = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 8, 10
        )
        cls_b = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 9, 11
        )

        request_enrollment(student_user.id, cls_a.id)
        conflicts = has_schedule_conflict(student_user.id, cls_b.id)
        assert len(conflicts) == 1

    def test_request_enrollment_blocks_on_conflict(
        self, db, student_user, course, teacher_user
    ):
        cls_a = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 8, 10
        )
        cls_b = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 9, 11
        )

        admin_enroll_student(student_user.id, cls_a.id, auto_approve=True)
        with pytest.raises(EnrollmentError, match="تداخل"):
            request_enrollment(student_user.id, cls_b.id)

    def test_exclude_enrollment_id(self, db, student_user, course, teacher_user):
        cls_a = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 8, 10
        )

        enrollment = admin_enroll_student(student_user.id, cls_a.id, auto_approve=True)
        conflicts = has_schedule_conflict(
            student_user.id, cls_a.id, exclude_enrollment_id=enrollment.id
        )
        assert conflicts == []

    def test_conflict_details(self, db, student_user, course, teacher_user):
        cls_a = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 8, 10
        )
        cls_b = self._make_class_with_schedule(
            db, course, teacher_user, "SATURDAY", 9, 11
        )

        admin_enroll_student(student_user.id, cls_a.id, auto_approve=True)
        details = get_schedule_conflict_details(student_user.id, cls_b.id)
        assert len(details) == 1
        assert details[0]["class_title"] == cls_a.title
        assert details[0]["weekday"] == "SATURDAY"

    def test_times_overlap_function(self):
        from app.application.enrollment.enrollment_service import _times_overlap

        # Partial overlap
        assert _times_overlap(time(8, 0), time(10, 0), time(9, 0), time(11, 0)) is True
        # Contiguous (no overlap)
        assert (
            _times_overlap(time(8, 0), time(10, 0), time(10, 0), time(12, 0)) is False
        )
        # Exact same time (conflict)
        assert _times_overlap(time(8, 0), time(10, 0), time(8, 0), time(10, 0)) is True
        # Contiguous start/end (no overlap)
        assert _times_overlap(time(8, 0), time(10, 0), time(7, 0), time(8, 0)) is False
        # Partial overlap from earlier
        assert _times_overlap(time(8, 0), time(10, 0), time(7, 0), time(9, 0)) is True
        # No overlap (later)
        assert (
            _times_overlap(time(8, 0), time(10, 0), time(11, 0), time(12, 0)) is False
        )
