"""Tests for Attendance services and routes."""

from datetime import date, time

import pytest

from app.application.academy.class_service import create_class
from app.application.academy.course_service import create_course
from app.application.attendance.attendance_service import (
    AttendanceError,
    compute_session_summary,
    compute_student_summary,
    get_eligible_enrollments,
    get_session_attendance,
    get_student_attendance,
    is_teacher_of_class,
    record_attendance,
    record_session_attendance,
)
from app.application.enrollment.enrollment_service import (
    admin_enroll_student,
    cancel_enrollment,
)
from app.infrastructure.database.models import (
    AttendanceModel,
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
    from datetime import date as date_type

    user = UserModel(login="student2")
    user.set_password("pass123")
    role = RoleModel.query.filter_by(name="STUDENT").first()
    user.roles.append(role)
    db.session.add(user)
    db.session.flush()

    profile = StudentProfileModel(
        user_id=user.id,
        first_name="Sara",
        last_name="Ahmadi",
        national_id="9876543210",
        mobile_phone="09129876543",
        birth_date=date_type(2001, 5, 20),
        gender="FEMALE",
    )
    db.session.add(profile)
    db.session.commit()
    return user


@pytest.fixture
def second_enrollment(db, second_student, academy_class):
    return admin_enroll_student(
        student_user_id=second_student.id,
        class_id=academy_class.id,
        auto_approve=True,
    )


@pytest.fixture
def teacher_assigned(db, teacher_user, academy_class):
    """Assign teacher to class."""
    from app.extensions import db as _db

    academy_class.teacher_user_id = teacher_user.id
    _db.session.commit()
    return teacher_user


@pytest.fixture
def other_teacher(db):
    """A teacher not assigned to any class."""
    user = UserModel(login="other_teacher")
    user.set_password("pass123")
    role = RoleModel(name="TEACHER")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user


class TestAttendanceCreation:
    """Tests for attendance record creation."""

    def test_create_attendance(self, db, enrollment, session, admin_user):
        attendance = record_attendance(
            enrollment_id=enrollment.id,
            session_id=session.id,
            status="PRESENT",
            note="On time",
            recorded_by=admin_user.id,
        )
        assert attendance.id is not None
        assert attendance.enrollment_id == enrollment.id
        assert attendance.session_id == session.id
        assert attendance.status == "PRESENT"
        assert attendance.note == "On time"
        assert attendance.recorded_by == admin_user.id
        assert attendance.recorded_at is not None
        assert attendance.updated_at is not None

    def test_create_attendance_all_statuses(self, db, enrollment, session, admin_user):
        for status in ("PRESENT", "ABSENT", "LATE", "EXCUSED"):
            attendance = record_attendance(
                enrollment_id=enrollment.id,
                session_id=session.id,
                status=status,
                recorded_by=admin_user.id,
            )
            assert attendance.status == status

    def test_create_attendance_invalid_status(self, db, enrollment, session):
        with pytest.raises(AttendanceError, match="Invalid status"):
            record_attendance(
                enrollment_id=enrollment.id,
                session_id=session.id,
                status="INVALID",
            )

    def test_create_attendance_nonexistent_enrollment(self, db, session):
        with pytest.raises(AttendanceError, match="Enrollment not found"):
            record_attendance(
                enrollment_id=9999,
                session_id=session.id,
                status="PRESENT",
            )

    def test_create_attendance_nonexistent_session(self, db, enrollment):
        with pytest.raises(AttendanceError, match="Session not found"):
            record_attendance(
                enrollment_id=enrollment.id,
                session_id=9999,
                status="PRESENT",
            )


class TestAttendanceIntegrity:
    """Tests for attendance relationship integrity."""

    def test_enrollment_session_same_class(self, db, enrollment, session, admin_user):
        """Enrollment and session must belong to the same class."""
        attendance = record_attendance(
            enrollment_id=enrollment.id,
            session_id=session.id,
            status="PRESENT",
            recorded_by=admin_user.id,
        )
        assert attendance.id is not None

    def test_enrollment_session_different_class(
        self, db, student_user, admin_user, course, mon_wed_schedule
    ):
        """Enrollment and session from different classes must be rejected."""
        class1 = create_class(
            course_id=course.id,
            title="Class 1",
            start_date=date(2026, 9, 7),
            capacity=5,
            schedule=mon_wed_schedule,
        )
        class2 = create_class(
            course_id=course.id,
            title="Class 2",
            start_date=date(2026, 9, 7),
            capacity=5,
            schedule=mon_wed_schedule,
        )

        enrollment = admin_enroll_student(
            student_user_id=student_user.id,
            class_id=class1.id,
            auto_approve=True,
        )

        from app.infrastructure.database.models import SessionModel

        session2 = SessionModel.query.filter_by(class_id=class2.id).first()

        with pytest.raises(AttendanceError, match="do not belong to the same class"):
            record_attendance(
                enrollment_id=enrollment.id,
                session_id=session2.id,
                status="PRESENT",
                recorded_by=admin_user.id,
            )

    def test_attendance_requires_approved_enrollment(
        self, db, student_user, academy_class, session, admin_user
    ):
        """Cannot record attendance for non-APPROVED enrollment."""
        enrollment = admin_enroll_student(
            student_user_id=student_user.id,
            class_id=academy_class.id,
            auto_approve=False,
        )
        assert enrollment.status == "PENDING"

        with pytest.raises(AttendanceError, match="approved enrollments"):
            record_attendance(
                enrollment_id=enrollment.id,
                session_id=session.id,
                status="PRESENT",
                recorded_by=admin_user.id,
            )

    def test_attendance_for_cancelled_enrollment(
        self, db, student_user, academy_class, session, admin_user
    ):
        """Cannot create new attendance for cancelled enrollment, but history preserved."""
        enrollment = admin_enroll_student(
            student_user_id=student_user.id,
            class_id=academy_class.id,
            auto_approve=True,
        )

        attendance = record_attendance(
            enrollment_id=enrollment.id,
            session_id=session.id,
            status="PRESENT",
            recorded_by=admin_user.id,
        )
        assert attendance.id is not None

        cancel_enrollment(enrollment)

        saved = AttendanceModel.query.get(attendance.id)
        assert saved is not None
        assert saved.status == "PRESENT"

        with pytest.raises(AttendanceError, match="approved enrollments"):
            record_attendance(
                enrollment_id=enrollment.id,
                session_id=session.id,
                status="ABSENT",
                recorded_by=admin_user.id,
            )


class TestDuplicatePrevention:
    """Tests for one attendance per enrollment per session."""

    def test_duplicate_prevented(self, db, enrollment, session, admin_user):
        """Updating existing attendance should not create a duplicate."""
        first = record_attendance(
            enrollment_id=enrollment.id,
            session_id=session.id,
            status="PRESENT",
            recorded_by=admin_user.id,
        )

        second = record_attendance(
            enrollment_id=enrollment.id,
            session_id=session.id,
            status="ABSENT",
            recorded_by=admin_user.id,
        )

        assert first.id == second.id
        assert second.status == "ABSENT"

        all_records = get_session_attendance(session.id)
        assert len(all_records) == 1

    def test_different_enrollments_same_session(
        self, db, enrollment, second_enrollment, session, admin_user
    ):
        """Different enrollments in same session can have separate attendance."""
        record_attendance(
            enrollment_id=enrollment.id,
            session_id=session.id,
            status="PRESENT",
            recorded_by=admin_user.id,
        )
        record_attendance(
            enrollment_id=second_enrollment.id,
            session_id=session.id,
            status="ABSENT",
            recorded_by=admin_user.id,
        )

        all_records = get_session_attendance(session.id)
        assert len(all_records) == 2


class TestBulkRecording:
    """Tests for bulk attendance recording."""

    def test_bulk_record(self, db, enrollment, second_enrollment, session, admin_user):
        """Bulk recording creates records for multiple students."""
        data = [
            {"enrollment_id": enrollment.id, "status": "PRESENT", "note": ""},
            {
                "enrollment_id": second_enrollment.id,
                "status": "LATE",
                "note": "5 min late",
            },
        ]
        results = record_session_attendance(
            session_id=session.id,
            attendance_data=data,
            recorded_by=admin_user.id,
        )
        assert len(results) == 2
        assert results[0].status == "PRESENT"
        assert results[1].status == "LATE"
        assert results[1].note == "5 min late"

    def test_bulk_record_updates_existing(
        self, db, enrollment, second_enrollment, session, admin_user
    ):
        """Bulk recording updates existing records instead of duplicating."""
        record_attendance(
            enrollment_id=enrollment.id,
            session_id=session.id,
            status="PRESENT",
            recorded_by=admin_user.id,
        )

        data = [
            {"enrollment_id": enrollment.id, "status": "ABSENT", "note": "changed"},
            {
                "enrollment_id": second_enrollment.id,
                "status": "EXCUSED",
                "note": "medical",
            },
        ]
        results = record_session_attendance(
            session_id=session.id,
            attendance_data=data,
            recorded_by=admin_user.id,
        )

        assert len(results) == 2
        all_records = get_session_attendance(session.id)
        assert len(all_records) == 2

        for r in all_records:
            if r.enrollment_id == enrollment.id:
                assert r.status == "ABSENT"
                assert r.note == "changed"

    def test_bulk_record_invalid_data(self, db, session):
        """Bulk recording with invalid data raises error."""
        data = [
            {"enrollment_id": 9999, "status": "PRESENT"},
        ]
        with pytest.raises(AttendanceError, match="Enrollment not found"):
            record_session_attendance(
                session_id=session.id,
                attendance_data=data,
            )

    def test_bulk_record_invalid_status(self, db, enrollment, session):
        """Bulk recording with invalid status raises error."""
        data = [
            {"enrollment_id": enrollment.id, "status": "INVALID"},
        ]
        with pytest.raises(AttendanceError, match="Invalid attendance data"):
            record_session_attendance(
                session_id=session.id,
                attendance_data=data,
            )


class TestQueries:
    """Tests for attendance queries."""

    def test_get_session_attendance(
        self, db, enrollment, second_enrollment, session, admin_user
    ):
        record_attendance(
            enrollment_id=enrollment.id,
            session_id=session.id,
            status="PRESENT",
            recorded_by=admin_user.id,
        )
        record_attendance(
            enrollment_id=second_enrollment.id,
            session_id=session.id,
            status="ABSENT",
            recorded_by=admin_user.id,
        )
        records = get_session_attendance(session.id)
        assert len(records) == 2

    def test_get_student_attendance(
        self, db, student_user, enrollment, session, admin_user
    ):
        record_attendance(
            enrollment_id=enrollment.id,
            session_id=session.id,
            status="LATE",
            recorded_by=admin_user.id,
        )
        records = get_student_attendance(student_user.id)
        assert len(records) == 1
        assert records[0].status == "LATE"

    def test_get_eligible_enrollments(self, db, enrollment, second_enrollment, session):
        eligible = get_eligible_enrollments(session.id)
        assert len(eligible) == 2

    def test_get_eligible_enrollments_excludes_pending(
        self, db, student_user, academy_class, session, mon_wed_schedule
    ):
        """Pending enrollments should not be eligible."""
        pending_enrollment = admin_enroll_student(
            student_user_id=student_user.id,
            class_id=academy_class.id,
            auto_approve=False,
        )
        assert pending_enrollment.status == "PENDING"

        eligible = get_eligible_enrollments(session.id)
        eligible_ids = [e.id for e in eligible]
        assert pending_enrollment.id not in eligible_ids


class TestSummary:
    """Tests for attendance summary computation."""

    def test_session_summary(
        self, db, enrollment, second_enrollment, session, admin_user
    ):
        record_attendance(
            enrollment_id=enrollment.id,
            session_id=session.id,
            status="PRESENT",
            recorded_by=admin_user.id,
        )
        record_attendance(
            enrollment_id=second_enrollment.id,
            session_id=session.id,
            status="ABSENT",
            recorded_by=admin_user.id,
        )
        summary = compute_session_summary(session.id)
        assert summary["PRESENT"] == 1
        assert summary["ABSENT"] == 1
        assert summary["LATE"] == 0
        assert summary["EXCUSED"] == 0
        assert summary["total"] == 2

    def test_student_summary(self, db, student_user, enrollment, session, admin_user):
        record_attendance(
            enrollment_id=enrollment.id,
            session_id=session.id,
            status="LATE",
            recorded_by=admin_user.id,
        )
        summary = compute_student_summary(student_user.id)
        assert summary["LATE"] == 1
        assert summary["total"] == 1


class TestAuthorization:
    """Tests for attendance authorization."""

    def test_is_teacher_of_class(self, db, teacher_assigned, academy_class):
        assert is_teacher_of_class(teacher_assigned.id, academy_class.id) is True

    def test_is_not_teacher_of_class(self, db, other_teacher, academy_class):
        assert is_teacher_of_class(other_teacher.id, academy_class.id) is False

    def test_is_teacher_nonexistent_class(self, db, teacher_assigned):
        assert is_teacher_of_class(teacher_assigned.id, 9999) is False


class TestHistoricalBehavior:
    """Tests for historical attendance preservation."""

    def test_cancelled_enrollment_preserves_attendance(
        self, db, student_user, academy_class, session, admin_user
    ):
        enrollment = admin_enroll_student(
            student_user_id=student_user.id,
            class_id=academy_class.id,
            auto_approve=True,
        )

        record_attendance(
            enrollment_id=enrollment.id,
            session_id=session.id,
            status="PRESENT",
            recorded_by=admin_user.id,
        )

        cancel_enrollment(enrollment)

        records = get_student_attendance(student_user.id)
        assert len(records) == 1
        assert records[0].status == "PRESENT"

    def test_modifying_attendance_updates_not_creates(
        self, db, enrollment, session, admin_user
    ):
        record_attendance(
            enrollment_id=enrollment.id,
            session_id=session.id,
            status="PRESENT",
            recorded_by=admin_user.id,
        )
        record_attendance(
            enrollment_id=enrollment.id,
            session_id=session.id,
            status="ABSENT",
            recorded_by=admin_user.id,
        )

        all_records = get_session_attendance(session.id)
        assert len(all_records) == 1
        assert all_records[0].status == "ABSENT"


class TestAttendanceRoutes:
    """Tests for attendance web routes."""

    def _login(self, client, user, password="adminpass123"):
        """Helper to log in a user."""
        return client.post(
            "/auth/login",
            data={"login": user.login, "password": password},
            follow_redirects=True,
        )

    def test_admin_attendance_list_requires_admin(self, client, teacher_user):
        self._login(client, teacher_user, "teacherpass123")
        resp = client.get("/attendance/admin/all")
        assert resp.status_code == 403

    def test_admin_attendance_list(self, client, admin_user):
        self._login(client, admin_user)
        resp = client.get("/attendance/admin/all")
        assert resp.status_code == 200

    def test_teacher_my_classes(self, client, teacher_assigned):
        self._login(client, teacher_assigned, "teacherpass123")
        resp = client.get("/attendance/teacher/my-classes")
        assert resp.status_code == 200

    def test_teacher_class_sessions(self, client, teacher_assigned, academy_class):
        self._login(client, teacher_assigned, "teacherpass123")
        resp = client.get(f"/attendance/teacher/class/{academy_class.id}/sessions")
        assert resp.status_code == 200

    def test_teacher_other_class_forbidden(self, client, other_teacher, academy_class):
        self._login(client, other_teacher, "pass123")
        resp = client.get(f"/attendance/teacher/class/{academy_class.id}/sessions")
        assert resp.status_code == 403

    def test_student_attendance_history(self, client, student_user):
        self._login(client, student_user, "studentpass123")
        resp = client.get("/attendance/student/my-attendance")
        assert resp.status_code == 200

    def test_student_cannot_access_admin_attendance(self, client, student_user):
        self._login(client, student_user, "studentpass123")
        resp = client.get("/attendance/admin/all")
        assert resp.status_code == 403

    def test_unauthenticated_redirect(self, client):
        resp = client.get("/attendance/admin/all")
        assert resp.status_code in (302, 401)
