"""Tests for Reporting and Analytics Service."""

from datetime import date, time, timedelta
from decimal import Decimal

import pytest

from app import create_app
from app.application.reporting.reporting_service import ReportingService
from app.extensions import db as _db
from app.infrastructure.database.models import (
    AcademyClassModel,
    ActivityModel,
    ActivitySubmissionModel,
    AssessmentModel,
    AssessmentResultModel,
    AttendanceModel,
    CourseModel,
    EnrollmentModel,
    FinancialTransactionModel,
    RoleModel,
    SessionModel,
    StudentProfileModel,
    TeacherProfileModel,
    UserModel,
)


@pytest.fixture(scope="session")
def app():
    """Create application for testing."""
    return create_app("testing")


@pytest.fixture(scope="function")
def db(app):
    """Create a fresh database for each test."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def admin_user(db):
    """Create an admin user for testing."""
    user = UserModel(login="admin")
    user.set_password("adminpass123")
    role = RoleModel(name="ADMIN")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def teacher_user(db):
    """Create a teacher user for testing."""
    user = UserModel(login="teacher")
    user.set_password("teacherpass123")
    role = RoleModel(name="TEACHER")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.flush()

    profile = TeacherProfileModel(
        user_id=user.id,
        first_name="Mohammad",
        last_name="Ahmadi",
        national_id="9876543210",
        mobile_phone="09129876543",
    )
    db.session.add(profile)
    db.session.commit()
    return user


@pytest.fixture
def student_user(db):
    """Create a student user for testing."""
    user = UserModel(login="student")
    user.set_password("studentpass123")
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
def course(db):
    """Create a course for testing."""
    course = CourseModel(
        title="Mathematics",
        description="Basic Mathematics",
        num_sessions=20,
        min_age=12,
        max_age=18,
    )
    db.session.add(course)
    db.session.commit()
    return course


@pytest.fixture
def academy_class(db, course, teacher_user):
    """Create a class for testing."""
    class_obj = AcademyClassModel(
        course_id=course.id,
        title="Math Class 101",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
        capacity=30,
        tuition=Decimal("500000"),
        num_sessions=20,
        status="ACTIVE",
        teacher_user_id=teacher_user.id,
    )
    db.session.add(class_obj)
    db.session.commit()
    return class_obj


@pytest.fixture
def enrollment(db, student_user, academy_class):
    """Create an enrollment for testing."""
    enrollment = EnrollmentModel(
        student_user_id=student_user.id,
        class_id=academy_class.id,
        status="APPROVED",
        approved_at=date.today(),
    )
    db.session.add(enrollment)
    db.session.commit()
    return enrollment


@pytest.fixture
def session(db, academy_class):
    """Create a session for testing."""
    session = SessionModel(
        class_id=academy_class.id,
        session_number=1,
        scheduled_date=date.today(),
        start_time=time(10, 0),
        end_time=time(12, 0),
        status="COMPLETED",
    )
    db.session.add(session)
    db.session.commit()
    return session


@pytest.fixture
def attendance(db, enrollment, session):
    """Create an attendance record for testing."""
    attendance = AttendanceModel(
        enrollment_id=enrollment.id,
        session_id=session.id,
        status="PRESENT",
        recorded_at=date.today(),
    )
    db.session.add(attendance)
    db.session.commit()
    return attendance


@pytest.fixture
def activity(db, academy_class):
    """Create an activity for testing."""
    activity = ActivityModel(
        type="HOMEWORK",
        title="Homework 1",
        description="First homework",
        requirement="REQUIRED",
        deadline=date.today() + timedelta(days=7),
        max_score=20,
        is_active=True,
        class_id=academy_class.id,
    )
    db.session.add(activity)
    db.session.commit()
    return activity


@pytest.fixture
def submission(db, activity, student_user, enrollment):
    """Create a submission for testing."""
    submission = ActivitySubmissionModel(
        activity_id=activity.id,
        student_user_id=student_user.id,
        enrollment_id=enrollment.id,
        text_content="My homework submission",
        submitted_at=date.today(),
        status="GRADED",
        score=18,
        version=1,
    )
    db.session.add(submission)
    db.session.commit()
    return submission


@pytest.fixture
def assessment(db, academy_class):
    """Create an assessment for testing."""
    assessment = AssessmentModel(
        class_id=academy_class.id,
        type="QUIZ",
        title="Quiz 1",
        description="First quiz",
        scheduled_date=date.today(),
        max_score=20,
        passing_score=10,
        status="GRADED",
    )
    db.session.add(assessment)
    db.session.commit()
    return assessment


@pytest.fixture
def assessment_result(db, assessment, enrollment, student_user):
    """Create an assessment result for testing."""
    result = AssessmentResultModel(
        assessment_id=assessment.id,
        enrollment_id=enrollment.id,
        student_user_id=student_user.id,
        score=15,
        max_score=20,
        percentage=75.0,
        result_status="GRADED",
        presence_status="PRESENT",
        pass_fail="PASS",
        graded_at=date.today(),
    )
    db.session.add(result)
    db.session.commit()
    return result


@pytest.fixture
def financial_transaction(db, student_user):
    """Create a financial transaction for testing."""
    transaction = FinancialTransactionModel(
        student_user_id=student_user.id,
        amount=Decimal("500000"),
        transaction_type="CHARGE",
        category="TUITION",
        description="Tuition fee",
        status="ACTIVE",
    )
    db.session.add(transaction)
    db.session.commit()
    return transaction


class TestReportingService:
    """Tests for ReportingService."""

    def test_get_admin_overview_empty(self, db):
        """Test admin overview with empty database."""
        overview = ReportingService.get_admin_overview()

        assert overview["students"]["total"] == 0
        assert overview["students"]["active"] == 0
        assert overview["teachers"]["total"] == 0
        assert overview["classes"]["total"] == 0
        assert overview["classes"]["active"] == 0
        assert overview["sessions"]["total"] == 0
        assert overview["sessions"]["upcoming"] == 0
        assert overview["enrollments"]["total"] == 0
        assert overview["enrollments"]["pending"] == 0
        assert overview["assessments"]["total"] == 0
        assert overview["assessments"]["graded"] == 0
        assert overview["finance"]["total_revenue"] == 0
        assert overview["finance"]["total_debt"] == 0
        assert overview["notifications"]["total"] == 0
        assert overview["notifications"]["failed"] == 0
        assert overview["attendance"]["percentage"] == 0
        assert overview["attendance"]["total"] == 0
        assert overview["attendance"]["present"] == 0

    def test_get_admin_overview_with_data(
        self,
        db,
        admin_user,
        teacher_user,
        student_user,
        academy_class,
        enrollment,
        session,
        attendance,
        assessment,
        assessment_result,
        financial_transaction,
    ):
        """Test admin overview with data."""
        overview = ReportingService.get_admin_overview()

        assert overview["students"]["total"] == 1
        assert overview["students"]["active"] == 1
        assert overview["teachers"]["total"] == 1
        assert overview["classes"]["total"] == 1
        assert overview["classes"]["active"] == 1
        assert overview["sessions"]["total"] == 1
        assert overview["enrollments"]["total"] == 1
        assert overview["enrollments"]["pending"] == 0
        assert overview["assessments"]["total"] == 1
        assert overview["assessments"]["graded"] == 1
        assert overview["finance"]["total_debt"] == 500000
        assert overview["attendance"]["total"] == 1
        assert overview["attendance"]["present"] == 1
        assert overview["attendance"]["percentage"] == 100.0

    def test_get_student_report(
        self,
        db,
        student_user,
        enrollment,
        academy_class,
        session,
        attendance,
        assessment,
        assessment_result,
        financial_transaction,
        activity,
        submission,
    ):
        """Test student report."""
        report = ReportingService.get_student_report(student_user.id)

        assert "error" not in report
        assert report["student"].id == student_user.id
        assert report["enrollments"]["total"] == 1
        assert report["enrollments"]["approved"] == 1
        assert report["attendance"]["total"] == 1
        assert report["attendance"]["present"] == 1
        assert report["attendance"]["percentage"] == 100.0
        assert report["activities"]["total_submitted"] == 1
        assert report["assessments"]["total"] == 1
        assert report["assessments"]["passed"] == 1
        assert report["finance"]["total_charges"] == 500000

    def test_get_student_report_not_found(self, db):
        """Test student report for non-existent student."""
        report = ReportingService.get_student_report(999999)
        assert "error" in report

    def test_get_class_report(
        self,
        db,
        academy_class,
        enrollment,
        session,
        attendance,
        teacher_user,
        assessment,
        activity,
    ):
        """Test class report."""
        report = ReportingService.get_class_report(academy_class.id)

        assert "error" not in report
        assert report["class"].id == academy_class.id
        assert report["enrollments"]["total"] == 1
        assert report["enrollments"]["approved"] == 1
        assert report["sessions"]["total"] == 1
        assert report["sessions"]["completed"] == 1
        assert report["attendance"]["total"] == 1
        assert report["attendance"]["present"] == 1
        assert report["attendance"]["percentage"] == 100.0
        assert report["activities"]["total"] == 1
        assert report["assessments"]["total"] == 1
        assert report["finance"]["total_tuition"] == 500000
        assert report["finance"]["capacity"] == 30
        assert report["finance"]["occupancy_rate"] == round(1 / 30 * 100, 1)

    def test_get_class_report_not_found(self, db):
        """Test class report for non-existent class."""
        report = ReportingService.get_class_report(999999)
        assert "error" in report

    def test_get_course_report(self, db, course, academy_class):
        """Test course report."""
        report = ReportingService.get_course_report(course.id)

        assert "error" not in report
        assert report["course"].id == course.id
        assert report["classes"]["total"] == 1
        assert report["classes"]["active"] == 1
        assert report["enrollments"]["total"] == 0
        assert report["activities"]["total"] == 0

    def test_get_course_report_not_found(self, db):
        """Test course report for non-existent course."""
        report = ReportingService.get_course_report(999999)
        assert "error" in report

    def test_get_attendance_report(self, db, enrollment, session, attendance):
        """Test attendance report."""
        report = ReportingService.get_attendance_report()

        assert report["total"] == 1
        assert report["present"] == 1
        assert report["absent"] == 0
        assert report["late"] == 0
        assert report["excused"] == 0
        assert report["percentage"] == 100.0

    def test_get_attendance_report_by_class(
        self, db, academy_class, enrollment, session, attendance
    ):
        """Test attendance report filtered by class."""
        report = ReportingService.get_attendance_report(class_id=academy_class.id)

        assert report["total"] == 1
        assert report["present"] == 1
        assert report["percentage"] == 100.0

    def test_get_attendance_report_by_student(
        self, db, student_user, enrollment, session, attendance
    ):
        """Test attendance report filtered by student."""
        report = ReportingService.get_attendance_report(student_user_id=student_user.id)

        assert report["total"] == 1
        assert report["present"] == 1
        assert report["percentage"] == 100.0

    def test_get_assessment_report(self, db, assessment, enrollment, assessment_result):
        """Test assessment report."""
        report = ReportingService.get_assessment_report(assessment.id)

        assert "error" not in report
        assert report["assessment"].id == assessment.id
        assert report["stats"]["eligible"] == 1
        assert report["stats"]["submitted"] == 1
        assert report["stats"]["missing"] == 0
        assert report["stats"]["average"] == 15.0
        assert report["stats"]["min"] == 15.0
        assert report["stats"]["max"] == 15.0
        assert report["stats"]["passed"] == 1
        assert report["stats"]["failed"] == 0
        assert report["stats"]["pass_rate"] == 100.0
        assert "score_distribution" in report["stats"]

    def test_get_assessment_report_not_found(self, db):
        """Test assessment report for non-existent assessment."""
        report = ReportingService.get_assessment_report(999999)
        assert "error" in report

    def test_get_activity_report(self, db, academy_class, activity, submission):
        """Test activity report."""
        report = ReportingService.get_activity_report(class_id=academy_class.id)

        assert report["total_activities"] == 1
        assert report["total_submissions"] == 1
        assert report["graded_submissions"] == 1
        assert report["average_grade"] == 18.0

    def test_get_activity_report_empty(self, db):
        """Test activity report with no activities."""
        report = ReportingService.get_activity_report()

        assert report["total_activities"] == 0
        assert report["total_submissions"] == 0
        assert report["completion_rate"] == 0

    def test_get_finance_report(self, db, student_user, financial_transaction):
        """Test finance report."""
        report = ReportingService.get_finance_report()

        assert report["total_charges"] == 500000
        assert report["total_payments"] == 0
        assert report["total_discounts"] == 0
        assert report["total_refunds"] == 0
        assert report["net_revenue"] == -500000
        assert len(report["debt_by_student"]) == 1
        assert report["debt_by_student"][0]["balance"] == -500000

    def test_get_enrollment_report(self, db, enrollment):
        """Test enrollment report."""
        report = ReportingService.get_enrollment_report()

        assert report["total"] == 1
        assert report["approved"] == 1
        assert report["pending"] == 0
        assert report["rejected"] == 0
        assert report["cancelled"] == 0
        assert report["approval_rate"] == 100.0

    def test_get_enrollment_report_by_class(self, db, academy_class, enrollment):
        """Test enrollment report filtered by class."""
        report = ReportingService.get_enrollment_report(class_id=academy_class.id)

        assert report["total"] == 1
        assert report["approved"] == 1

    def test_get_teacher_report(
        self,
        db,
        teacher_user,
        academy_class,
        enrollment,
        session,
        attendance,
        activity,
        assessment,
    ):
        """Test teacher report."""
        report = ReportingService.get_teacher_report(teacher_user.id)

        assert "error" not in report
        assert report["teacher"].id == teacher_user.id
        assert report["classes"]["total"] == 1
        assert report["classes"]["active"] == 1
        assert report["students"]["total"] == 1
        assert report["sessions"]["total"] == 1
        assert report["sessions"]["completed"] == 1
        assert report["activities"]["total"] == 1
        assert report["assessments"]["total"] == 1

    def test_get_teacher_report_not_found(self, db):
        """Test teacher report for non-existent teacher."""
        report = ReportingService.get_teacher_report(999999)
        assert "error" in report

    def test_get_operational_report_empty(self, db):
        """Test operational report with empty database."""
        report = ReportingService.get_operational_report()

        assert report["today_classes"] == []
        assert report["upcoming_sessions"] == 0
        assert report["pending_enrollments"] == 0
        assert report["sessions_without_attendance"] == 0
        assert report["failed_notifications"] == 0
        assert report["unpaid_balances"] == 0

    def test_get_notification_report_empty(self, db):
        """Test notification report with empty database."""
        report = ReportingService.get_notification_report()

        assert report["total"] == 0
        assert report["sent"] == 0
        assert report["failed"] == 0
        assert report["pending"] == 0
        assert report["success_rate"] == 0
        assert report["channels"] == []

    def test_get_attendance_alerts_empty(self, db):
        """Test attendance alerts with no data."""
        alerts = ReportingService.get_attendance_alerts()
        assert alerts == []

    def test_get_attendance_alerts_with_low_attendance(
        self, db, student_user, enrollment, session
    ):
        """Test attendance alerts for students with low attendance."""
        # Create absent attendance
        attendance = AttendanceModel(
            enrollment_id=enrollment.id,
            session_id=session.id,
            status="ABSENT",
            recorded_at=date.today(),
        )
        db.session.add(attendance)
        db.session.commit()

        alerts = ReportingService.get_attendance_alerts(threshold=70.0)
        assert len(alerts) == 1
        assert alerts[0]["student_id"] == student_user.id
        assert alerts[0]["attendance_percentage"] == 0.0

    def test_get_finance_report_with_date_filter(
        self, db, student_user, financial_transaction
    ):
        """Test finance report with date filters."""
        report = ReportingService.get_finance_report(
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
        )

        assert report["total_charges"] == 500000

    def test_get_attendance_report_with_date_filter(
        self, db, enrollment, session, attendance
    ):
        """Test attendance report with date filters."""
        report = ReportingService.get_attendance_report(
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
        )

        assert report["total"] == 1
        assert report["present"] == 1

    def test_get_enrollment_report_by_course(
        self, db, course, academy_class, enrollment
    ):
        """Test enrollment report filtered by course."""
        report = ReportingService.get_enrollment_report(course_id=course.id)

        assert report["total"] == 1
        assert report["approved"] == 1

    def test_get_enrollment_report_no_classes(self, db, course):
        """Test enrollment report for course with no classes."""
        report = ReportingService.get_enrollment_report(course_id=course.id)

        assert report["total"] == 0
        assert report["approval_rate"] == 0

    def test_get_student_report_with_multiple_enrollments(
        self, db, student_user, course, enrollment
    ):
        """Test student report with multiple enrollments."""
        # Create another class
        class2 = AcademyClassModel(
            course_id=course.id,
            title="Math Class 201",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
            capacity=25,
            tuition=Decimal("600000"),
            num_sessions=20,
            status="ACTIVE",
        )
        db.session.add(class2)
        db.session.flush()

        # Create another enrollment
        enrollment2 = EnrollmentModel(
            student_user_id=student_user.id,
            class_id=class2.id,
            status="PENDING",
        )
        db.session.add(enrollment2)
        db.session.commit()

        report = ReportingService.get_student_report(student_user.id)

        assert report["enrollments"]["total"] == 2
        assert report["enrollments"]["approved"] == 1
        assert report["enrollments"]["pending"] == 1

    def test_get_class_report_with_capacity(self, db, academy_class):
        """Test class report capacity calculation."""
        report = ReportingService.get_class_report(academy_class.id)

        assert report["finance"]["capacity"] == 30
        assert report["finance"]["occupancy_rate"] == 0.0

    def test_get_attendance_report_empty_class(self, db, academy_class):
        """Test attendance report for class with no attendance."""
        report = ReportingService.get_attendance_report(class_id=academy_class.id)

        assert report["total"] == 0
        assert report["percentage"] == 0

    def test_get_assessment_report_score_distribution(
        self, db, assessment, enrollment, student_user
    ):
        """Test assessment report score distribution."""
        # Get or create STUDENT role
        role = db.session.query(RoleModel).filter_by(name="STUDENT").first()
        if not role:
            role = RoleModel(name="STUDENT")
            db.session.add(role)
            db.session.flush()

        # Create multiple results with different scores
        scores = [5, 12, 18, 20]
        for i, score in enumerate(scores):
            user = UserModel(login=f"student{i}")
            user.set_password("pass123")
            user.roles.append(role)
            db.session.add(user)
            db.session.flush()

            profile = StudentProfileModel(
                user_id=user.id,
                first_name="Student",
                last_name=f"{i}",
                national_id=f"100000000{i}",
                mobile_phone=f"0912123456{i}",
                birth_date=date(2000, 1, 15),
                gender="MALE",
            )
            db.session.add(profile)

            enr = EnrollmentModel(
                student_user_id=user.id,
                class_id=assessment.class_id,
                status="APPROVED",
                approved_at=date.today(),
            )
            db.session.add(enr)
            db.session.flush()

            result = AssessmentResultModel(
                assessment_id=assessment.id,
                enrollment_id=enr.id,
                student_user_id=user.id,
                score=score,
                max_score=20,
                percentage=score / 20 * 100,
                result_status="GRADED",
                presence_status="PRESENT",
                pass_fail="PASS" if score >= 10 else "FAIL",
                graded_at=date.today(),
            )
            db.session.add(result)

        db.session.commit()

        report = ReportingService.get_assessment_report(assessment.id)

        assert report["stats"]["submitted"] == 4
        assert report["stats"]["min"] == 5.0
        assert report["stats"]["max"] == 20.0

    def test_get_finance_report_with_payments(self, db, student_user):
        """Test finance report with payments."""
        # Create charge
        charge = FinancialTransactionModel(
            student_user_id=student_user.id,
            amount=Decimal("500000"),
            transaction_type="CHARGE",
            category="TUITION",
            description="Tuition fee",
            status="ACTIVE",
        )
        db.session.add(charge)

        # Create payment
        payment = FinancialTransactionModel(
            student_user_id=student_user.id,
            amount=Decimal("300000"),
            transaction_type="PAYMENT",
            category="TUITION",
            description="Partial payment",
            status="ACTIVE",
        )
        db.session.add(payment)

        # Create discount
        discount = FinancialTransactionModel(
            student_user_id=student_user.id,
            amount=Decimal("50000"),
            transaction_type="DISCOUNT",
            category="SCHOLARSHIP",
            description="Scholarship discount",
            status="ACTIVE",
        )
        db.session.add(discount)

        db.session.commit()

        report = ReportingService.get_finance_report()

        assert report["total_charges"] == 500000
        assert report["total_payments"] == 300000
        assert report["total_discounts"] == 50000
        # net_revenue = payments + discounts - refunds - charges
        # = 300000 + 50000 - 0 - 500000 = -150000
        assert report["net_revenue"] == -150000

    def test_get_enrollment_report_with_rejected(self, db, student_user, academy_class):
        """Test enrollment report with rejected enrollments."""
        # Create rejected enrollment
        enrollment = EnrollmentModel(
            student_user_id=student_user.id,
            class_id=academy_class.id,
            status="REJECTED",
        )
        db.session.add(enrollment)
        db.session.commit()

        report = ReportingService.get_enrollment_report()

        assert report["total"] == 1
        assert report["rejected"] == 1
        assert report["approval_rate"] == 0.0

    def test_get_teacher_report_no_classes(self, db, teacher_user):
        """Test teacher report with no classes."""
        report = ReportingService.get_teacher_report(teacher_user.id)

        assert report["classes"]["total"] == 0
        assert report["students"]["total"] == 0
        assert report["sessions"]["total"] == 0
        assert report["activities"]["total"] == 0
        assert report["assessments"]["total"] == 0
