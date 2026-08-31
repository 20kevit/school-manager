"""Seed script for MVP testing.

Usage::

    .venv\\Scripts\\activate
    $env:FLASK_APP="run.py"
    python seed.py

This uses db.create_all() to create tables directly from models.
Do NOT use ``flask db upgrade`` -- some migrations have SQLite compatibility issues.
"""

import os
import sys
from datetime import date, datetime, time
from decimal import Decimal

# Delete old database if it exists
db_path = os.path.join(os.path.dirname(__file__), "instance", "school_manager_dev.db")
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Deleted old database: {db_path}")

from app import create_app  # noqa: E402
from app.application.auth.services import assign_role, create_user  # noqa: E402
from app.extensions import db  # noqa: E402
from app.infrastructure.database.models import (  # noqa: E402
    AcademyClassModel,
    ActivityModel,
    AssessmentModel,
    AttendanceModel,
    ClassScheduleModel,
    CourseModel,
    EnrollmentModel,
    FinancialTransactionModel,
    ParentProfileModel,
    SessionModel,
    StudentProfileModel,
    SyllabusItemModel,
    TeacherProfileModel,
    UserModel,
)

app = create_app("development")
with app.app_context():
    db.create_all()
    print("All tables created.")

    if UserModel.query.filter_by(login="admin").first() is not None:
        print("Users already exist. Skipping seed.")
        sys.exit(0)

    # ── Users ──────────────────────────────────────────────────────────
    admin = create_user("admin", "admin123")
    assign_role(admin, "ADMIN")
    print("Created: admin / admin123")

    teacher = create_user("teacher1", "teacher123")
    assign_role(teacher, "TEACHER")
    teacher_profile = TeacherProfileModel(
        user_id=teacher.id,
        first_name="Reza",
        last_name="Ahmadi",
        national_id="1122334455",
        mobile_phone="09131112233",
    )
    db.session.add(teacher_profile)
    db.session.flush()
    print("Created: teacher1 / teacher123")

    student = create_user("student1", "student123")
    assign_role(student, "STUDENT")
    student_profile = StudentProfileModel(
        user_id=student.id,
        first_name="Ali",
        last_name="Rezaei",
        national_id="1234567890",
        mobile_phone="09121234567",
        birth_date=date(2008, 5, 15),
        gender="MALE",
    )
    db.session.add(student_profile)
    db.session.flush()
    print("Created: student1 / student123")

    parent = create_user("parent1", "parent123")
    assign_role(parent, "PARENT")
    parent_profile = ParentProfileModel(
        user_id=parent.id,
        first_name="Mohammad",
        last_name="Rezaei",
        national_id="9876543210",
        mobile_phone="09129876543",
    )
    db.session.add(parent_profile)
    db.session.flush()
    parent_profile.children.append(student_profile)
    print("Created: parent1 / parent123 (linked to student1)")

    # ── Course ─────────────────────────────────────────────────────────
    course = CourseModel(
        title="ریاضی پایه هفتم",
        description="دوره جامع ریاضی پایه هفتم شامل جبر، هندسه و آمار",
        num_sessions=4,
        min_age=12,
        max_age=14,
        prerequisites="",
    )
    db.session.add(course)
    db.session.flush()

    for i, title in enumerate(
        ["مقدمه جبر", "معادلات خطی", "هندسه توصیفی", "آمار و احتمال"], start=1
    ):
        db.session.add(
            SyllabusItemModel(
                course_id=course.id,
                order=i,
                title=title,
                description=f"توضیحات {title}",
            )
        )
    print("Created: course + 4 syllabus items")

    # ── Class ──────────────────────────────────────────────────────────
    academy_class = AcademyClassModel(
        course_id=course.id,
        title="کلاس ریاضی هفتم - گروه الف",
        start_date=date(2026, 9, 1),
        capacity=25,
        num_sessions=4,
        tuition=Decimal("5000000"),
        status="ACTIVE",
        teacher_user_id=teacher.id,
    )
    db.session.add(academy_class)
    db.session.flush()

    db.session.add(
        ClassScheduleModel(
            class_id=academy_class.id,
            weekday="SATURDAY",
            start_time=time(10, 0),
            end_time=time(12, 0),
        )
    )
    db.session.add(
        ClassScheduleModel(
            class_id=academy_class.id,
            weekday="TUESDAY",
            start_time=time(10, 0),
            end_time=time(12, 0),
        )
    )
    print("Created: class + schedule")

    # ── Sessions ───────────────────────────────────────────────────────
    session_dates = [
        date(2026, 9, 5),
        date(2026, 9, 8),
        date(2026, 9, 12),
        date(2026, 9, 15),
    ]
    sessions = []
    for i, sdate in enumerate(session_dates, start=1):
        sess = SessionModel(
            class_id=academy_class.id,
            session_number=i,
            scheduled_date=sdate,
            start_time=time(10, 0),
            end_time=time(12, 0),
            status="COMPLETED" if i <= 2 else "SCHEDULED",
            title=f"جلسه {i}",
        )
        db.session.add(sess)
        sessions.append(sess)
    db.session.flush()
    print("Created: 4 sessions")

    # ── Enrollment ─────────────────────────────────────────────────────
    enrollment = EnrollmentModel(
        student_user_id=student.id,
        class_id=academy_class.id,
        status="APPROVED",
        requested_at=datetime(2026, 8, 25),
        approved_at=datetime(2026, 8, 26),
    )
    db.session.add(enrollment)
    db.session.flush()
    print("Created: enrollment (APPROVED)")

    # ── Attendance ─────────────────────────────────────────────────────
    for sess in sessions[:2]:
        db.session.add(
            AttendanceModel(
                enrollment_id=enrollment.id,
                session_id=sess.id,
                status="PRESENT",
                recorded_by=teacher.id,
            )
        )
    print("Created: 2 attendance records")

    # ── Activity ───────────────────────────────────────────────────────
    db.session.add(
        ActivityModel(
            type="HOMEWORK",
            title="تمرین فصل اول",
            description="تمرین‌های فصل اول جبر",
            class_id=academy_class.id,
            max_score=100,
        )
    )
    print("Created: 1 activity")

    # ── Assessment ─────────────────────────────────────────────────────
    db.session.add(
        AssessmentModel(
            class_id=academy_class.id,
            type="QUIZ",
            title="آزمون میان‌ترم",
            description="آزمون میان‌ترم ریاضی هفتم",
            scheduled_date=date(2026, 9, 15),
            max_score=20,
            passing_score=10,
            status="SCHEDULED",
            created_by=teacher.id,
        )
    )
    print("Created: 1 assessment")

    # ── Finance ────────────────────────────────────────────────────────
    db.session.add(
        FinancialTransactionModel(
            student_user_id=student.id,
            amount=Decimal("5000000"),
            transaction_type="CHARGE",
            category="TUITION",
            description="شهریه کلاس ریاضی هفتم - گروه الف",
            class_id=academy_class.id,
            enrollment_id=enrollment.id,
            created_by=admin.id,
        )
    )
    db.session.add(
        FinancialTransactionModel(
            student_user_id=student.id,
            amount=Decimal("2000000"),
            transaction_type="PAYMENT",
            category="TUITION",
            description="پرداخت نقدی - قسط اول",
            payment_method="CASH",
            class_id=academy_class.id,
            created_by=admin.id,
        )
    )
    db.session.add(
        FinancialTransactionModel(
            student_user_id=student.id,
            amount=Decimal("500000"),
            transaction_type="DISCOUNT",
            category="TUITION",
            description="تخفیف ویژه ثبت‌نام زودهنگام",
            class_id=academy_class.id,
            created_by=admin.id,
        )
    )
    print("Created: 3 finance records")

    db.session.commit()
    print("\nSeed complete!")
    print("Login credentials:")
    print("  Admin:   admin / admin123")
    print("  Teacher: teacher1 / teacher123")
    print("  Student: student1 / student123")
    print("  Parent:  parent1 / parent123")
