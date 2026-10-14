"""Complete deterministic synthetic-academy generator for the demo environment.

Demo only. Never import or invoke this module against production.

Safety model (fail-closed):
  1. ``assert_demo_environment()`` refuses unless ALL hold:
     - ``DEMO_MODE=true`` in the process environment,
     - ``DATABASE_URL`` positively contains the demo database name,
     - the live connection's ``current_database()`` is the demo database.
  2. No production database URL is ever used as a fallback: missing demo
     configuration raises instead of connecting anywhere.
  3. ``reset_demo_data()`` uses an explicit table allowlist and never touches
     ``alembic_version``.

Generator properties:
  - Deterministic: ``random.seed(DEMO_SEED)`` plus stable fixture tables.
  - Idempotent: every entity is created with get-or-create on a natural key,
    so repeated runs do not duplicate the academy.
  - Relationally consistent: enrollments reference real students/classes,
    attendance references approved enrollments and same-class sessions,
    grades reference eligible enrollments, finance uses the real
    ``finance_service`` so balances reconcile by construction.
  - Auditable: returns per-entity counts.
"""

from __future__ import annotations

import os
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

DEMO_DATABASE_NAME = "school_manager_demo"
DEMO_SEED = 20261014
DEMO_PASSWORD = "12345678"
DEMO_SEED_VERSION = "2026.10-demo.1"

# ---------------------------------------------------------------------------
# Safety guard
# ---------------------------------------------------------------------------


class NotDemoEnvironmentError(RuntimeError):
    """Raised when a demo-only operation is attempted outside the demo."""


def assert_demo_environment() -> str:
    """Prove the active environment/database is the demo. Fail closed.

    Returns the verified database name. Raises NotDemoEnvironmentError
    (a RuntimeError) on any mismatch or missing configuration.
    """
    if os.environ.get("DEMO_MODE", "").lower() != "true":
        raise NotDemoEnvironmentError(
            "Refusing demo seed/reset: DEMO_MODE is not 'true'. "
            "Set DEMO_MODE=true only in the demo environment file."
        )
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or DEMO_DATABASE_NAME not in db_url:
        raise NotDemoEnvironmentError(
            "Refusing demo seed/reset: DATABASE_URL does not positively "
            "identify the demo database. Missing demo configuration must "
            "fail instead of falling back to any other database."
        )
    # Positive connection identity (not hostname naming alone).
    from sqlalchemy import text

    from app.extensions import db

    try:
        current_db = db.session.execute(text("SELECT current_database()")).scalar()
    except Exception as exc:
        raise NotDemoEnvironmentError(
            f"Refusing demo seed/reset: cannot establish database identity ({exc})."
        ) from exc
    if current_db != DEMO_DATABASE_NAME:
        raise NotDemoEnvironmentError(
            f"Refusing demo seed/reset: connected to {current_db!r}, "
            f"expected {DEMO_DATABASE_NAME!r}."
        )
    return current_db


# ---------------------------------------------------------------------------
# Fixture tables (Persian, fictional identities only)
# ---------------------------------------------------------------------------

MALE_FIRST = [
    "علی",
    "محمد",
    "رضا",
    "حسین",
    "امیر",
    "مهدی",
    "سعید",
    "حسن",
    "کریم",
    "مصطفی",
    "احمد",
    "سجاد",
    "ایمان",
    "میلاد",
    "پوریا",
    "آرش",
    "کیان",
    "دانیال",
    "سینا",
    "پارسا",
]
FEMALE_FIRST = [
    "سارا",
    "زهرا",
    "فاطمه",
    "مهسا",
    "نیلوفر",
    "پریسا",
    "مریم",
    "حانیه",
    "غزل",
    "یلدا",
    "مهدیه",
    "سعیده",
    "نوشین",
    "صبا",
    "سحر",
    "عسل",
    "ترانه",
    "رویا",
    "نگار",
    "الهام",
]
LAST = [
    "رضایی",
    "احمدی",
    "حسینی",
    "محمدی",
    "رحیمی",
    "خانی",
    "مرادی",
    "کریمی",
    "هاشمی",
    "امیری",
    "جعفری",
    "ابراهیمی",
    "فلاحی",
    "موسوی",
    "صفدری",
    "شاهرخ",
    "توکلی",
    "قربانی",
    "داوودی",
    "رستمی",
    "اکبری",
    "نوری",
    "جلیلی",
    "زارعی",
    "صالحی",
    "فرهادی",
    "باقری",
    "مالکی",
    "نصیری",
    "کاظمی",
]

COURSES = [
    ("ریاضی پایه هفتم", "دوره جامع ریاضی پایه هفتم: جبر، هندسه و آمار", 16, 12, 14),
    ("ریاضی کنکور", "دوره فشرده ریاضی کنکور: جبر، هندسه تحلیلی و احتمال", 20, 16, 19),
    ("فیزیک پایه دهم", "مکانیک، حرکت‌شناسی و نیرو", 16, 15, 16),
    ("فیزیک کنکور", "مرور جامع فیزیک کنکور با حل تست", 18, 16, 19),
    ("شیمی یازدهم", "مسائل شیمیایی و الکتروشیمی", 14, 16, 17),
    ("زیست‌شناسی دهم", "سلول، بافت و فیزیولوژی گیاهی", 14, 15, 16),
    ("زبان انگلیسی پیشرفته", "گرامر، واژگان و مکالمه", 18, 12, 18),
    ("زبان انگلیسی کودکان", "بازی و مکالمه برای گروه سنی کودک", 12, 8, 11),
    ("برنامه‌نویسی پایتون", "مبانی برنامه‌نویسی و حل مسئله با پایتون", 16, 13, 18),
    ("شطرنج مقدماتی", "قوانین، تاکتیک‌های پایه و شروع‌بازی", 12, 7, 14),
]

WEEKDAYS = [
    "SATURDAY",
    "SUNDAY",
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
]

SCHEDULES = [
    [("SATURDAY", 8, 0, 10, 0), ("MONDAY", 8, 0, 10, 0)],
    [("SUNDAY", 10, 0, 12, 0), ("WEDNESDAY", 10, 0, 12, 0)],
    [("SATURDAY", 14, 0, 16, 0), ("TUESDAY", 14, 0, 16, 0)],
    [("MONDAY", 16, 0, 18, 0), ("THURSDAY", 16, 0, 18, 0)],
    [("SUNDAY", 8, 0, 10, 0), ("THURSDAY", 8, 0, 10, 0)],
    [("TUESDAY", 10, 0, 12, 0), ("FRIDAY", 10, 0, 12, 0)],
]

ASSESSMENT_TYPES = ["QUIZ", "MIDTERM", "FINAL_EXAM", "PROJECT", "PRACTICAL", "ORAL"]
ATTENDANCE_STATES = ["PRESENT", "ABSENT", "LATE", "EXCUSED"]


def _nid(i: int) -> str:
    """Deterministic unique 10-digit national id for fixture index i."""
    return f"{4000000000 + i}"[:10]


def _phone(i: int) -> str:
    return f"0912{(1000000 + (i * 7919) % 8999999):07d}"


def _email(login: str) -> str:
    return f"{login}@example.com"


# ---------------------------------------------------------------------------
# Reset (demo only)
# ---------------------------------------------------------------------------

# Explicit allowlist — alembic_version is deliberately absent.
_RESET_TABLES = [
    "grade_history",
    "assessment_results",
    "assessments",
    "grading_components",
    "grading_templates",
    "attendances",
    "session_edit_history",
    "sessions",
    "class_session_contents",
    "financial_transactions",
    "activity_files",
    "activity_submissions",
    "activities",
    "enrollments",
    "class_schedules",
    "teacher_payments",
    "teacher_contracts",
    "stored_files",
    "notification_deliveries",
    "in_app_notifications",
    "notification_preferences",
    "notification_templates",
    "notifications",
    "audit_logs",
    "academy_classes",
    "syllabus_items",
    "courses",
    "semesters",
    "academic_years",
    "academic_calendar_events",
    "parent_student",
    "student_profiles",
    "teacher_profiles",
    "parent_profiles",
    "login_attempts",
    "user_roles",
    "users",
    "roles",
]


def reset_demo_data(db) -> dict:
    """Delete all demo rows (demo database only) and report the outcome."""
    assert_demo_environment()
    from sqlalchemy import text

    tables = ", ".join(_RESET_TABLES)
    db.session.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    db.session.commit()
    return {"truncated_tables": len(_RESET_TABLES), "database": DEMO_DATABASE_NAME}


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------


def seed_demo_full(db) -> dict:
    """Build the complete synthetic academy. Idempotent. Returns counts."""
    assert_demo_environment()
    random.seed(DEMO_SEED)

    from app.application.finance import finance_service
    from app.infrastructure.database.models import (
        AcademicCalendarEventModel,
        AcademicYearModel,
        AcademyClassModel,
        ActivityModel,
        ActivitySubmissionModel,
        AssessmentModel,
        AssessmentResultModel,
        AttendanceModel,
        ClassScheduleModel,
        CourseModel,
        EnrollmentModel,
        FinancialTransactionModel,
        GradeHistoryModel,
        InAppNotificationModel,
        ParentProfileModel,
        RoleModel,
        SemesterModel,
        SessionEditHistoryModel,
        SessionModel,
        StudentProfileModel,
        SyllabusItemModel,
        TeacherContractModel,
        TeacherPaymentModel,
        TeacherProfileModel,
        UserModel,
    )

    stats = {
        "seed_version": DEMO_SEED_VERSION,
        "users": 0,
        "courses": 0,
        "classes": 0,
        "enrollments": 0,
        "sessions": 0,
        "attendances": 0,
        "activities": 0,
        "submissions": 0,
        "assessments": 0,
        "results": 0,
        "transactions": 0,
        "contracts": 0,
        "payments": 0,
    }
    today = date.today()
    now = datetime.now()

    # -- Roles ----------------------------------------------------------
    for role_name in ("ADMIN", "TEACHER", "STUDENT", "PARENT"):
        if not RoleModel.query.get(role_name):
            db.session.add(RoleModel(name=role_name))
    db.session.flush()

    def get_or_create_user(login, role, **profile_kw):
        user = UserModel.query.filter_by(login=login).first()
        created = False
        if user is None:
            user = UserModel(login=login)
            user.set_password(DEMO_PASSWORD)
            user.must_change_password = False
            db.session.add(user)
            db.session.flush()
            user.roles.append(RoleModel.query.get(role))
            created = True
            stats["users"] += 1
        return user, created

    # -- Users ----------------------------------------------------------
    admin, _ = get_or_create_user("admin", "ADMIN")
    staff_users = []
    for i in (1, 2, 3):
        u, _ = get_or_create_user(f"staff{i}", "ADMIN")
        staff_users.append(u)
    # One inactive staff account (blocked-state scenario).
    blocked_staff, _ = get_or_create_user("staff_blocked", "ADMIN")
    if blocked_staff.is_active_user:
        blocked_staff.is_active_user = False

    teachers = []
    for i in range(1, 13):
        login = f"teacher{i}"
        user, created = get_or_create_user(login, "TEACHER")
        teachers.append(user)
        if created:
            first = (MALE_FIRST + FEMALE_FIRST)[(i * 3) % 40]
            last = LAST[(i * 5) % len(LAST)]
            db.session.add(
                TeacherProfileModel(
                    user_id=user.id,
                    first_name=first,
                    last_name=last,
                    national_id=_nid(1000 + i),
                    mobile_phone=_phone(1000 + i),
                )
            )
    # Teacher with no current classes (edge case): last teacher is left
    # unassigned by the class builder below.
    db.session.flush()

    students = []
    for i in range(1, 101):
        login = f"student{i}"
        user, created = get_or_create_user(login, "STUDENT")
        students.append(user)
        if created:
            female = (i % 10) < 4
            first = (
                FEMALE_FIRST[i % len(FEMALE_FIRST)]
                if female
                else MALE_FIRST[i % len(MALE_FIRST)]
            )
            last = LAST[i % len(LAST)]
            # ~10 adult students (18+) so student finance visibility works;
            # the rest are minors spanning supported ages.
            if i % 10 == 0:
                birth = date(2005 + (i % 2), (i % 12) + 1, (i % 27) + 1)
            else:
                birth = date(2008 + (i % 9), (i % 12) + 1, (i % 27) + 1)
            db.session.add(
                StudentProfileModel(
                    user_id=user.id,
                    first_name=first,
                    last_name=last,
                    national_id=_nid(2000 + i),
                    mobile_phone=_phone(2000 + i),
                    birth_date=birth,
                    gender="FEMALE" if female else "MALE",
                )
            )
    # One inactive student (blocked-state scenario).
    blocked_student = UserModel.query.filter_by(login="student99").first()
    if blocked_student is not None and blocked_student.is_active_user:
        blocked_student.is_active_user = False
    db.session.flush()

    parents = []
    for i in range(1, 9):
        login = f"parent{i}"
        user, created = get_or_create_user(login, "PARENT")
        parents.append(user)
        if created:
            db.session.add(
                ParentProfileModel(
                    user_id=user.id,
                    first_name=MALE_FIRST[(i * 7) % len(MALE_FIRST)],
                    last_name=LAST[(i * 11) % len(LAST)],
                    national_id=_nid(3000 + i),
                    mobile_phone=_phone(3000 + i),
                )
            )
    db.session.flush()

    # Parent-child links (deterministic spread).
    all_student_profiles = StudentProfileModel.query.order_by(
        StudentProfileModel.id
    ).all()
    for i, parent in enumerate(parents):
        prof = ParentProfileModel.query.filter_by(user_id=parent.id).first()
        if prof is None:
            continue
        for k in range(2):
            idx = (i * 12 + k * 5) % len(all_student_profiles)
            child = all_student_profiles[idx]
            if child not in prof.children:
                prof.children.append(child)
    db.session.flush()

    # -- Academic calendar ----------------------------------------------
    year1 = AcademicYearModel.query.filter_by(title="۱۴۰۳-۱۴۰۴").first()
    if year1 is None:
        year1 = AcademicYearModel(
            title="۱۴۰۳-۱۴۰۴",
            start_date=today - timedelta(days=400),
            end_date=today - timedelta(days=40),
            is_active=False,
        )
        db.session.add(year1)
        db.session.flush()
    year2 = AcademicYearModel.query.filter_by(title="۱۴۰۴-۱۴۰۵").first()
    if year2 is None:
        year2 = AcademicYearModel(
            title="۱۴۰۴-۱۴۰۵",
            start_date=today - timedelta(days=39),
            end_date=today + timedelta(days=326),
            is_active=True,
        )
        db.session.add(year2)
        db.session.flush()
    sem_defs = [
        (
            year1,
            "نیمسال اول ۱۴۰۳",
            today - timedelta(days=400),
            today - timedelta(days=220),
            False,
        ),
        (
            year1,
            "نیمسال دوم ۱۴۰۳",
            today - timedelta(days=219),
            today - timedelta(days=40),
            False,
        ),
        (
            year2,
            "نیمسال اول ۱۴۰۴",
            today - timedelta(days=39),
            today + timedelta(days=140),
            True,
        ),
        (
            year2,
            "نیمسال دوم ۱۴۰۴",
            today + timedelta(days=141),
            today + timedelta(days=326),
            False,
        ),
    ]
    semesters = []
    for year, title, s, e, active in sem_defs:
        sem = SemesterModel.query.filter_by(title=title).first()
        if sem is None:
            sem = SemesterModel(
                academic_year_id=year.id,
                title=title,
                start_date=s,
                end_date=e,
                is_active=active,
            )
            db.session.add(sem)
            db.session.flush()
        semesters.append(sem)
    for ev_title, s, e in [
        ("تعطیلات نوروز", today - timedelta(days=200), today - timedelta(days=187)),
        ("تعطیلات تابستانی", today - timedelta(days=90), today - timedelta(days=76)),
        ("روز معلم", today + timedelta(days=20), today + timedelta(days=20)),
    ]:
        if AcademicCalendarEventModel.query.filter_by(title=ev_title).first() is None:
            db.session.add(
                AcademicCalendarEventModel(
                    title=ev_title,
                    start_date=s,
                    end_date=e,
                    is_recurring=False,
                    description=f"رویداد تقویمی نمایشی: {ev_title}",
                )
            )
    db.session.flush()

    # -- Courses ----------------------------------------------------------
    courses = []
    for title, desc, num_s, min_age, max_age in COURSES:
        course = CourseModel.query.filter_by(title=title).first()
        if course is None:
            course = CourseModel(
                title=title,
                description=desc,
                num_sessions=num_s,
                min_age=min_age,
                max_age=max_age,
            )
            db.session.add(course)
            db.session.flush()
            for j in range(1, 4):
                db.session.add(
                    SyllabusItemModel(
                        course_id=course.id,
                        order=j,
                        title=f"فصل {j}",
                        description=f"سرفصل {j} از {title}",
                    )
                )
            stats["courses"] += 1
        courses.append(course)
    db.session.flush()

    # -- Classes: 40 across statuses and 12 months -------------------------
    # Cohorts: historical (completed), current (active), upcoming (planned),
    # plus cancelled. Deterministic assignment, capacity edge cases.
    class_statuses = (
        ["COMPLETED"] * 16 + ["ACTIVE"] * 14 + ["PLANNED"] * 5 + ["CANCELLED"] * 5
    )
    classes = []
    for idx in range(40):
        title = f"کلاس {courses[idx % len(courses)].title} — گروه {chr(0x627 + (idx % 4))}{idx // 10 + 1}"
        existing = AcademyClassModel.query.filter_by(title=title).first()
        if existing is not None:
            classes.append(existing)
            continue
        status = class_statuses[idx]
        if status == "COMPLETED":
            start = today - timedelta(days=360 - (idx % 16) * 12)
        elif status == "ACTIVE":
            start = today - timedelta(days=20 + (idx % 14) * 4)
        elif status == "PLANNED":
            start = today + timedelta(days=10 + (idx % 5) * 12)
        else:
            start = today - timedelta(days=60 + (idx % 5) * 20)
        course = courses[idx % len(courses)]
        # Capacity edge cases: class 0 full-ish small, class 1 large,
        # one zero-enrollment planned class is left empty below.
        if idx == 0:
            capacity = 8
        elif idx == 1:
            capacity = 40
        else:
            capacity = 10 + (idx % 16)
        tuition = [350000, 400000, 450000, 500000, 550000, 600000][idx % 6]
        # Teachers 1..11 teach; teacher12 stays class-free (edge case).
        teacher = teachers[idx % 11]
        sem = semesters[2] if start >= semesters[2].start_date else semesters[1]
        cls = AcademyClassModel(
            course_id=course.id,
            title=title,
            start_date=start,
            end_date=start + timedelta(days=90),
            capacity=capacity,
            tuition=tuition,
            num_sessions=course.num_sessions or 12,
            status=status,
            teacher_user_id=teacher.id,
            semester_id=sem.id,
            online_link=(
                f"https://example.com/online/{idx + 1}" if idx % 3 == 0 else None
            ),
        )
        db.session.add(cls)
        db.session.flush()
        sched = SCHEDULES[idx % len(SCHEDULES)]
        for wd, sh, sm, eh, em in sched:
            db.session.add(
                ClassScheduleModel(
                    class_id=cls.id,
                    weekday=wd,
                    start_time=time(sh, sm),
                    end_time=time(eh, em),
                )
            )
        db.session.flush()
        # Sessions spread across the class period.
        n = int(cls.num_sessions)
        step = max(1, 90 // max(n, 1))
        for s in range(1, n + 1):
            sdate = start + timedelta(days=(s - 1) * step)
            if sdate < today - timedelta(days=1):
                sstatus = "CANCELLED" if (idx + s) % 17 == 0 else "COMPLETED"
            elif sdate <= today + timedelta(days=1):
                sstatus = "SCHEDULED"
            else:
                sstatus = "SCHEDULED"
            if status == "CANCELLED":
                sstatus = "CANCELLED" if s % 2 == 0 else "SCHEDULED"
            elif status == "PLANNED":
                sstatus = "SCHEDULED"
            db.session.add(
                SessionModel(
                    class_id=cls.id,
                    session_number=s,
                    scheduled_date=sdate,
                    start_time=time(sched[0][1], sched[0][2]),
                    end_time=time(sched[0][3], sched[0][4]),
                    status=sstatus,
                    title=f"جلسه {s}",
                    online_link=(
                        f"https://example.com/live/{cls.id}/{s}"
                        if idx % 4 == 0 and s == 1
                        else None
                    ),
                )
            )
        db.session.flush()
        # One rescheduled-session history entry per completed class.
        if status == "COMPLETED":
            first_session = SessionModel.query.filter_by(
                class_id=cls.id, session_number=1
            ).first()
            if (
                first_session is not None
                and SessionEditHistoryModel.query.filter_by(
                    session_id=first_session.id
                ).first()
                is None
            ):
                db.session.add(
                    SessionEditHistoryModel(
                        session_id=first_session.id,
                        edited_by=teacher.id,
                        change_type="RESCHEDULE",
                        previous_date=first_session.scheduled_date,
                        new_date=first_session.scheduled_date,
                        previous_title=first_session.title,
                        new_title=first_session.title,
                    )
                )
        stats["classes"] += 1
        classes.append(cls)
    db.session.flush()

    # -- Enrollments: all statuses, capacity + duplicate edge cases ---------
    def add_enrollment(student, cls, status, req_days_ago, decide_days_ago=None):
        # Active pair (PENDING/APPROVED) must be unique per student+class
        # (business rule), and the schema additionally enforces uniqueness
        # per (student, class, status) — check both before inserting.
        if (
            EnrollmentModel.query.filter_by(student_user_id=student.id, class_id=cls.id)
            .filter(EnrollmentModel.status.in_(["PENDING", "APPROVED"]))
            .first()
            is not None
        ):
            return None
        if (
            EnrollmentModel.query.filter_by(
                student_user_id=student.id, class_id=cls.id, status=status
            ).first()
            is not None
        ):
            return None
        req = now - timedelta(days=req_days_ago)
        decided = (
            (now - timedelta(days=decide_days_ago))
            if decide_days_ago is not None
            else None
        )
        enr = EnrollmentModel(
            student_user_id=student.id,
            class_id=cls.id,
            status=status,
            requested_at=req,
            approved_at=decided if status == "APPROVED" else None,
            rejected_at=decided if status == "REJECTED" else None,
            cancelled_at=decided if status == "CANCELLED" else None,
        )
        db.session.add(enr)
        db.session.flush()
        stats["enrollments"] += 1
        return enr

    approved_enrollments: list = []
    # Fill class 0 to capacity (full-class scenario) with old dates.
    for k, student in enumerate(students[: classes[0].capacity]):
        enr = add_enrollment(student, classes[0], "APPROVED", 300 - k, 295 - k)
        if enr is not None:
            approved_enrollments.append(enr)
    # One extra pending request on the full class (capacity-blocked scenario).
    add_enrollment(students[60], classes[0], "PENDING", 3)
    # Broad spread: approved across active/completed, pending awaiting action,
    # rejected and cancelled histories across months.
    for i, student in enumerate(students):
        target = classes[(i % 34) + 2]  # skip class 0/1 mostly; class 39 stays empty
        if target.status == "CANCELLED" and i % 3:
            continue
        r = (i * 37) % 100
        req_ago = 20 + (i * 13) % 330
        if r < 62:
            enr = add_enrollment(
                student, target, "APPROVED", req_ago, max(1, req_ago - 5)
            )
            if enr is not None and target.status in ("ACTIVE", "COMPLETED"):
                approved_enrollments.append(enr)
        elif r < 74:
            add_enrollment(student, target, "PENDING", (i % 20) + 1)
        elif r < 87:
            add_enrollment(student, target, "REJECTED", req_ago, max(1, req_ago - 3))
        else:
            add_enrollment(student, target, "CANCELLED", req_ago, max(1, req_ago - 2))
    # Students with no enrollments (edge case): student100 gets none
    # (loop above covers index 0..99 for students[0..99]; remove any rows
    # accidentally created for the last student to keep the empty-state).
    last_student = students[-1]
    for enr in EnrollmentModel.query.filter_by(student_user_id=last_student.id).all():
        db.session.delete(enr)
    db.session.flush()

    # -- Second enrollment per student (list/filter/pagination depth) --------------
    # Different class family from the first pass; deterministic statuses.
    for i, student in enumerate(students[:-1]):
        target = classes[((i * 7 + 5) % 36) + 2]  # classes 2..37
        if target.status == "CANCELLED" and i % 2:
            continue
        r = (i * 53) % 100
        req_ago = 10 + (i * 11) % 300
        if r < 55:
            enr = add_enrollment(
                student, target, "APPROVED", req_ago, max(1, req_ago - 4)
            )
            if enr is not None and target.status in ("ACTIVE", "COMPLETED"):
                approved_enrollments.append(enr)
        elif r < 70:
            add_enrollment(student, target, "PENDING", (i % 15) + 1)
        elif r < 85:
            add_enrollment(student, target, "REJECTED", req_ago, max(1, req_ago - 2))
        else:
            add_enrollment(student, target, "CANCELLED", req_ago, max(1, req_ago - 1))
    # Populate the large class 1 (capacity 40) for near-capacity filters.
    for k, student in enumerate(students[20:45]):
        r = (k * 29) % 100
        if r < 75:
            enr = add_enrollment(
                student, classes[1], "APPROVED", 60 - (k % 50), 55 - (k % 50)
            )
            if enr is not None and classes[1].status in ("ACTIVE", "COMPLETED"):
                approved_enrollments.append(enr)
        elif r < 90:
            add_enrollment(student, classes[1], "PENDING", (k % 10) + 1)
        else:
            add_enrollment(student, classes[1], "REJECTED", 40, 38)
    db.session.flush()

    # -- Attendance ----------------------------------------------------------
    for enr in approved_enrollments:
        sessions = (
            SessionModel.query.filter_by(class_id=enr.class_id, status="COMPLETED")
            .order_by(SessionModel.session_number)
            .all()
        )
        if not sessions:
            continue
        # Coverage mix: some sessions fully recorded, some partially,
        # some with no records (leave every 5th session empty).
        for s in sessions:
            if s.session_number % 5 == 0:
                continue
            if AttendanceModel.query.filter_by(
                enrollment_id=enr.id, session_id=s.id
            ).first():
                continue
            h = (enr.id * 31 + s.id * 17) % 100
            if h < 70:
                st = "PRESENT"
            elif h < 80:
                st = "ABSENT"
            elif h < 90:
                st = "LATE"
            else:
                st = "EXCUSED"
            db.session.add(
                AttendanceModel(
                    enrollment_id=enr.id,
                    session_id=s.id,
                    status=st,
                    note="ثبت نمایشی حضوروغیاب" if st == "EXCUSED" else "",
                    recorded_by=admin.id,
                )
            )
            stats["attendances"] += 1
            if stats["attendances"] % 400 == 0:
                db.session.flush()
    db.session.flush()

    # -- Activities + submissions ----------------------------------------------
    act_types = ["HOMEWORK", "PROJECT", "QUIZ", "PRACTICE"]
    for ci, cls in enumerate(classes[:20]):
        for a in range(3):
            title = f"فعالیت {a + 1} — {cls.title[:30]}"
            act = ActivityModel.query.filter_by(class_id=cls.id, title=title).first()
            if act is None:
                act = ActivityModel(
                    type=act_types[(ci + a) % len(act_types)],
                    title=title,
                    description=f"شرح نمایشی فعالیت {a + 1} برای {cls.title}",
                    requirement="REQUIRED" if a < 2 else "OPTIONAL",
                    max_score=100,
                    class_id=cls.id,
                    is_active=not (ci == 11 and a == 2),  # one deactivated activity
                )
                db.session.add(act)
                db.session.flush()
                stats["activities"] += 1
            class_enrs = (
                EnrollmentModel.query.filter_by(class_id=cls.id, status="APPROVED")
                .order_by(EnrollmentModel.id)
                .all()[:6]
            )
            for enr in class_enrs:
                if ActivitySubmissionModel.query.filter_by(
                    activity_id=act.id, enrollment_id=enr.id
                ).first():
                    continue
                h = (act.id * 13 + enr.id * 7) % 100
                if h < 45:
                    sst, score = "GRADED", Decimal(str(50 + (h % 51)))
                elif h < 65:
                    sst, score = "SUBMITTED", None
                elif h < 75:
                    sst, score = "RETURNED", None
                else:
                    continue  # not submitted (edge case)
                db.session.add(
                    ActivitySubmissionModel(
                        activity_id=act.id,
                        student_user_id=enr.student_user_id,
                        enrollment_id=enr.id,
                        text_content=f"پاسخ نمایشی {act.title}",
                        submitted_at=now - timedelta(days=(h % 20) + 1),
                        status=sst,
                        score=score,
                        feedback="بازخورد نمایشی مدرس" if sst == "GRADED" else "",
                        graded_at=now - timedelta(days=h % 10)
                        if sst == "GRADED"
                        else None,
                        graded_by=admin.id if sst == "GRADED" else None,
                    )
                )
                stats["submissions"] += 1
    db.session.flush()

    # -- Assessments + results + grade history ----------------------------------
    for ci, cls in enumerate(classes[:20]):
        for a in range(2):
            atype = ASSESSMENT_TYPES[(ci + a) % len(ASSESSMENT_TYPES)]
            title = f"{atype} — {cls.title[:24]}"
            asm = AssessmentModel.query.filter_by(class_id=cls.id, title=title).first()
            if asm is None:
                # Status spread incl. empty (DRAFT, no grades) and cancelled.
                pool = ["DRAFT", "SCHEDULED", "OPEN", "CLOSED", "GRADED", "CANCELLED"]
                astatus = pool[(ci + a) % len(pool)]
                max_sc = (
                    Decimal("20") if atype in ("QUIZ", "MIDTERM") else Decimal("100")
                )
                sched = None
                if astatus != "DRAFT":
                    sched = today - timedelta(days=(ci * 9 + a * 4) % 200)
                asm = AssessmentModel(
                    class_id=cls.id,
                    type=atype,
                    title=title,
                    description=f"ارزیابی نمایشی {title}",
                    scheduled_date=sched,
                    max_score=max_sc,
                    passing_score=max_sc / 2,
                    penalty_factor=Decimal("0.5")
                    if atype == "QUIZ" and a == 0
                    else Decimal("0"),
                    status=astatus,
                    created_by=teachers[ci % 11].id,
                )
                db.session.add(asm)
                db.session.flush()
                stats["assessments"] += 1
            if asm.status in ("CLOSED", "GRADED"):
                class_enrs = (
                    EnrollmentModel.query.filter_by(class_id=cls.id, status="APPROVED")
                    .order_by(EnrollmentModel.id)
                    .all()
                )
                for enr in class_enrs:
                    if AssessmentResultModel.query.filter_by(
                        assessment_id=asm.id, enrollment_id=enr.id
                    ).first():
                        continue
                    h = (asm.id * 29 + enr.id * 11) % 100
                    maxf = float(asm.max_score)
                    if h < 8:
                        # Absent / excused presence states.
                        db.session.add(
                            AssessmentResultModel(
                                assessment_id=asm.id,
                                enrollment_id=enr.id,
                                student_user_id=enr.student_user_id,
                                score=None,
                                max_score=asm.max_score,
                                percentage=None,
                                result_status="NOT_GRADED",
                                presence_status="ABSENT" if h < 4 else "EXCUSED",
                                pass_fail="NOT_DETERMINED",
                                graded_by=teachers[ci % 11].id,
                                graded_at=now - timedelta(days=h % 15),
                            )
                        )
                    else:
                        raw = round(maxf * (0.35 + (h % 65) / 100), 1)
                        if asm.penalty_factor and h % 7 == 0:
                            wrong = 2
                            eff = max(0.0, raw - wrong * float(asm.penalty_factor))
                        else:
                            wrong = None
                            eff = raw
                        passed = eff >= float(asm.passing_score)
                        res = AssessmentResultModel(
                            assessment_id=asm.id,
                            enrollment_id=enr.id,
                            student_user_id=enr.student_user_id,
                            score=Decimal(str(eff)),
                            wrong_count=wrong,
                            max_score=asm.max_score,
                            percentage=round(eff / maxf * 100, 1),
                            result_status="GRADED",
                            presence_status="PRESENT",
                            pass_fail="PASS" if passed else "FAIL",
                            graded_by=teachers[ci % 11].id,
                            graded_at=now - timedelta(days=h % 15),
                        )
                        db.session.add(res)
                        db.session.flush()
                        # Grade correction history on a deterministic subset.
                        if h % 23 == 0:
                            old = max(0.0, eff - 2.0)
                            db.session.add(
                                GradeHistoryModel(
                                    result_id=res.id,
                                    previous_score=Decimal(str(old)),
                                    new_score=Decimal(str(eff)),
                                    previous_pass_fail="PASS"
                                    if old >= float(asm.passing_score)
                                    else "FAIL",
                                    new_pass_fail="PASS" if passed else "FAIL",
                                    corrected_by=teachers[ci % 11].id,
                                    reason="اصلاح نمایشی نمره",
                                )
                            )
                    stats["results"] += 1
                    if stats["results"] % 300 == 0:
                        db.session.flush()
    db.session.flush()

    # -- Finance via real services (balances reconcile by construction) ---------
    for enr in approved_enrollments:
        cls = AcademyClassModel.query.get(enr.class_id)
        if cls is None or Decimal(str(cls.tuition)) <= 0:
            continue
        try:
            finance_service.create_tuition_charge(
                enr.student_user_id, cls.id, enr.id, created_by=admin.id
            )
            stats["transactions"] += 1
        except finance_service.FinanceError:
            pass  # idempotent re-run: charge already exists
        db.session.flush()
        charge = (
            FinancialTransactionModel.query.filter_by(
                enrollment_id=enr.id,
                category="TUITION",
                transaction_type="CHARGE",
                status="ACTIVE",
            )
            .order_by(FinancialTransactionModel.id)
            .first()
        )
        # Backdate tuition charges across 12 months for historical reports.
        if charge is not None and charge.created_at >= now - timedelta(days=2):
            charge.created_at = enr.requested_at
        h = (enr.id * 41) % 100
        payment = None
        if h < 55:
            # Fully paid.
            try:
                payment = finance_service.record_payment(
                    enr.student_user_id,
                    Decimal(str(charge.amount if charge is not None else cls.tuition)),
                    payment_method=["CASH", "CARD", "BANK_TRANSFER", "ONLINE"][
                        enr.id % 4
                    ],
                    description=f"پرداخت شهریه {cls.title}",
                    reference_number=f"DEMO-REF-{enr.id:06d}",
                    enrollment_id=enr.id,
                    class_id=cls.id,
                    created_by=admin.id,
                )
                stats["transactions"] += 1
            except finance_service.FinanceError:
                payment = (
                    FinancialTransactionModel.query.filter_by(
                        enrollment_id=enr.id,
                        transaction_type="PAYMENT",
                        status="ACTIVE",
                    )
                    .order_by(FinancialTransactionModel.id)
                    .first()
                )
        elif h < 80:
            # Partial payment (outstanding balance scenario).
            try:
                payment = finance_service.record_payment(
                    enr.student_user_id,
                    (
                        Decimal(
                            str(charge.amount if charge is not None else cls.tuition)
                        )
                        // 2
                    ),
                    payment_method="CARD",
                    description=f"پیش‌پرداخت شهریه {cls.title}",
                    reference_number=f"DEMO-PART-{enr.id:06d}",
                    enrollment_id=enr.id,
                    class_id=cls.id,
                    created_by=admin.id,
                )
                stats["transactions"] += 1
            except finance_service.FinanceError:
                payment = (
                    FinancialTransactionModel.query.filter_by(
                        enrollment_id=enr.id,
                        transaction_type="PAYMENT",
                        status="ACTIVE",
                    )
                    .order_by(FinancialTransactionModel.id)
                    .first()
                )
        # else: unpaid (debt scenario).
        if payment is not None and payment.created_at >= now - timedelta(days=2):
            payment.created_at = (enr.approved_at or enr.requested_at) + timedelta(
                days=3
            )
        # Discount subset.
        if enr.id % 9 == 0:
            try:
                finance_service.apply_discount(
                    enr.student_user_id,
                    Decimal("50000"),
                    category="TUITION",
                    description=f"تخفیف ثبت‌نام زودهنگام {cls.title}",
                    enrollment_id=enr.id,
                    class_id=cls.id,
                    created_by=admin.id,
                )
                stats["transactions"] += 1
            except finance_service.FinanceError:
                pass
        # Full + partial refunds (linked to real payments only).
        if payment is not None and enr.id % 25 == 0:
            try:
                finance_service.record_refund(
                    enr.student_user_id,
                    Decimal(str(payment.amount)),
                    description="بازپرداخت کامل نمایشی (انصراف)",
                    related_transaction_id=payment.id,
                    created_by=admin.id,
                )
                stats["transactions"] += 1
            except finance_service.FinanceError:
                pass
        elif payment is not None and enr.id % 21 == 0:
            try:
                finance_service.record_refund(
                    enr.student_user_id,
                    Decimal(str(payment.amount)) // 2,
                    description="بازپرداخت جزئی نمایشی",
                    related_transaction_id=payment.id,
                    created_by=admin.id,
                )
                stats["transactions"] += 1
            except finance_service.FinanceError:
                pass
        if stats["transactions"] % 200 == 0:
            db.session.flush()
    # Reversal of one discount (history preserved, impact undone).
    disc = (
        FinancialTransactionModel.query.filter_by(
            transaction_type="DISCOUNT", status="ACTIVE"
        )
        .order_by(FinancialTransactionModel.id)
        .first()
    )
    if (
        disc is not None
        and FinancialTransactionModel.query.filter_by(
            related_transaction_id=disc.id, transaction_type="REVERSAL"
        ).first()
        is None
    ):
        try:
            finance_service.reverse_transaction(
                disc.id, description="ابطال نمایشی تخفیف", reversed_by=admin.id
            )
            stats["transactions"] += 1
        except finance_service.FinanceError:
            pass
    # Correction of one payment (original CORRECTED, replacement created).
    # Idempotent marker: skip entirely once the demo correction exists.
    if (
        FinancialTransactionModel.query.filter_by(
            description="تصحیح نمایشی پرداخت"
        ).first()
        is None
    ):
        pay = (
            FinancialTransactionModel.query.filter_by(
                transaction_type="PAYMENT", status="ACTIVE"
            )
            .order_by(FinancialTransactionModel.id)
            .first()
        )
        if pay is not None:
            try:
                finance_service.correct_transaction(
                    pay.id,
                    new_amount=Decimal(str(pay.amount)),
                    new_description="تصحیح نمایشی پرداخت",
                    corrected_by=admin.id,
                )
                stats["transactions"] += 1
            except finance_service.FinanceError:
                pass
    # Goodwill credit (adjustment without underlying payment).
    if (
        FinancialTransactionModel.query.filter_by(
            description="اعتبار حسن‌نیت نمایشی"
        ).first()
        is None
    ):
        finance_service.record_goodwill_credit(
            students[5].id,
            Decimal("100000"),
            reason="اعتبار حسن‌نیت نمایشی",
            created_by=admin.id,
        )
        stats["transactions"] += 1
    # Pending + failed online payments (gateway sandbox simulation).
    for k, sid in enumerate([s.id for s in students[70:76]]):
        ref = f"DEMO-AUTH-{k:04d}"
        if (
            FinancialTransactionModel.query.filter_by(reference_number=ref).first()
            is None
        ):
            db.session.add(
                FinancialTransactionModel(
                    student_user_id=sid,
                    amount=Decimal("450000"),
                    transaction_type="PAYMENT",
                    category="TUITION",
                    description="پرداخت آنلاین نمایشی (در انتظار تأیید درگاه)",
                    reference_number=ref,
                    gateway_ref_id=f"DEMO-GW-{k:04d}",
                    payment_method="ONLINE",
                    status="PENDING" if k % 2 == 0 else "FAILED",
                    created_by=sid,
                )
            )
            stats["transactions"] += 1
    db.session.flush()

    # -- Payroll: contracts + finalized/pending payments -------------------------
    for ti, teacher in enumerate(teachers[:11]):
        cls = classes[ti % len(classes)]
        if (
            TeacherContractModel.query.filter_by(
                teacher_user_id=teacher.id, class_id=cls.id
            ).first()
            is None
        ):
            db.session.add(
                TeacherContractModel(
                    teacher_user_id=teacher.id,
                    class_id=cls.id,
                    payment_type="PER_SESSION"
                    if ti % 2 == 0
                    else "PERCENTAGE_OF_REVENUE",
                    rate=Decimal("150000") if ti % 2 == 0 else Decimal("25"),
                    is_active=True,
                )
            )
            stats["contracts"] += 1
    # One generic fallback contract.
    if (
        TeacherContractModel.query.filter_by(
            teacher_user_id=teachers[0].id, class_id=None
        ).first()
        is None
    ):
        db.session.add(
            TeacherContractModel(
                teacher_user_id=teachers[0].id,
                class_id=None,
                payment_type="PER_SESSION",
                rate=Decimal("120000"),
                is_active=True,
            )
        )
        stats["contracts"] += 1
    db.session.flush()
    for mi in range(3):
        p_start = today - timedelta(days=30 * (mi + 1))
        p_end = today - timedelta(days=30 * mi + 1)
        for ti, teacher in enumerate(teachers[:6]):
            if (
                TeacherPaymentModel.query.filter_by(
                    teacher_user_id=teacher.id, period_start=p_start, period_end=p_end
                ).first()
                is None
            ):
                gross = Decimal(str(800000 + ti * 150000 + mi * 50000))
                db.session.add(
                    TeacherPaymentModel(
                        teacher_user_id=teacher.id,
                        period_start=p_start,
                        period_end=p_end,
                        gross_amount=gross,
                        deductions=Decimal("0"),
                        net_amount=gross,
                        status="PAID" if mi > 0 else "PENDING",
                        paid_at=now - timedelta(days=30 * mi) if mi > 0 else None,
                    )
                )
                stats["payments"] += 1
    # One voided payment (VOIDED status scenario).
    if TeacherPaymentModel.query.filter_by(status="VOIDED").first() is None:
        db.session.add(
            TeacherPaymentModel(
                teacher_user_id=teachers[6].id,
                period_start=today - timedelta(days=90),
                period_end=today - timedelta(days=61),
                gross_amount=Decimal("500000"),
                deductions=Decimal("0"),
                net_amount=Decimal("500000"),
                status="VOIDED",
            )
        )
        stats["payments"] += 1
    db.session.flush()

    # -- In-app notifications (announcement + samples) ------------------------------
    if (
        InAppNotificationModel.query.filter_by(title="راهنمای محیط نمایشی").first()
        is None
    ):
        for u in [admin, *teachers[:3], *students[:10]]:
            db.session.add(
                InAppNotificationModel(
                    user_id=u.id,
                    title="راهنمای محیط نمایشی",
                    message=(
                        "این یک محیط نمایشی با داده‌های مصنوعی است. "
                        "پرداخت‌ها و پیامک‌های واقعی غیرفعال‌اند."
                    ),
                    notification_type="ANNOUNCEMENT",
                    read_status="UNREAD",
                )
            )
    db.session.commit()

    # -- Final recount (auditable; reflects idempotent state) ------------------------
    stats["users"] = UserModel.query.count()
    stats["courses"] = CourseModel.query.count()
    stats["classes"] = AcademyClassModel.query.count()
    stats["enrollments"] = EnrollmentModel.query.count()
    stats["sessions"] = SessionModel.query.count()
    stats["attendances"] = AttendanceModel.query.count()
    stats["activities"] = ActivityModel.query.count()
    stats["submissions"] = ActivitySubmissionModel.query.count()
    stats["assessments"] = AssessmentModel.query.count()
    stats["results"] = AssessmentResultModel.query.count()
    stats["transactions"] = FinancialTransactionModel.query.count()
    stats["contracts"] = TeacherContractModel.query.count()
    stats["payments"] = TeacherPaymentModel.query.count()
    return stats
