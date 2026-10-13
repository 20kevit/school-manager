"""Rich demo data generator for flask seed-demo command."""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

PERSIAN_MALE_FIRST_NAMES = [
    "Ali",
    "Mohammad",
    "Reza",
    "Hossein",
    "Amir",
    "Mehdi",
    "Saeed",
    "Hassan",
    "Karim",
    "Mostafa",
    "Ahmad",
    "Mahdi",
    "Sajjad",
    "Iman",
    "Milad",
    "Pouria",
    "Arash",
    "Kian",
    "Danial",
    "Sina",
    "Parsa",
    "Arian",
    "Navid",
    "Omid",
]

PERSIAN_FEMALE_FIRST_NAMES = [
    "Sara",
    "Zahra",
    "Fateme",
    "Mahsa",
    "Nastaran",
    "Parisa",
    "Maryam",
    "Hanieh",
    "Ghazal",
    "Yalda",
    "Mahdieh",
    "Saeede",
    "Noushin",
    "Saba",
    "Sahar",
    "Asal",
    "Tara",
    "Roya",
    "Negar",
    "Elham",
    "Shirin",
    "Nazanin",
]

PERSIAN_LAST_NAMES = [
    "Rezaei",
    "Ahmadi",
    "Hosseini",
    "Mohammadi",
    "Rahimi",
    "Khani",
    "Moradi",
    "Karimi",
    "Hashemi",
    "Amiri",
    "Jafari",
    "Ebrahimi",
    "Fallahi",
    "Mousavi",
    "Safdari",
    "Pourmohammadi",
    "Shahrokhi",
    "Tavakoli",
    "Ghorbani",
    "Davoudi",
    "Rostami",
    "Akbari",
    "Nouri",
    "Jalili",
    "Zarei",
    "Salehi",
    "Farhadi",
    "Bagheri",
    "Maleki",
]

COURSES = [
    ("ریاضی پایه هفتم", "دوره ریاضی پایه هفتم شامل جبر، هندسه و آمار", 20, 11, 13),
    ("فیزیک پایه دهم", "دوره فیزیک پایه دهم شامل مکانیک، حرکت و نیرو", 16, 15, 16),
    ("شیمی یازدهم", "دوره شیمی یازدهم شامل مسائل شیمیایی و الکتروشیمی", 14, 16, 17),
    (
        "زبان انگلیسی پیشرفته",
        "دوره زبان انگلیسی شامل گرامر، واژگان و مکالمه",
        18,
        12,
        18,
    ),
]

CLASS_TITLES = [
    "گروه الف",
    "گروه ب",
    "گروه ج",
]

TEACHER_NAMES = [
    ("Reza", "Ahmadi"),
    ("Sara", "Mohammadi"),
    ("Hossein", "Karimi"),
]

WEEKDAY_SCHEDULES = [
    [("SATURDAY", 8, 0, 10, 0), ("MONDAY", 8, 0, 10, 0)],
    [("SUNDAY", 10, 0, 12, 0), ("WEDNESDAY", 10, 0, 12, 0)],
    [("SATURDAY", 14, 0, 16, 0), ("TUESDAY", 14, 0, 16, 0)],
    [("MONDAY", 16, 0, 18, 0), ("THURSDAY", 16, 0, 18, 0)],
    [("SUNDAY", 8, 0, 10, 0), ("THURSDAY", 8, 0, 10, 0)],
]


def _pick(lst):
    return random.choice(lst)


def _national_id():
    return str(random.randint(1000000000, 9999999999))


def _phone():
    return f"0912{random.randint(1000000, 9999999)}"


def seed_demo_data(db) -> dict:
    """Generate rich demo data. Returns stats dict."""
    from app.infrastructure.database.models import (
        AcademyClassModel,
        ActivityModel,
        AssessmentModel,
        AssessmentResultModel,
        AttendanceModel,
        ClassScheduleModel,
        CourseModel,
        EnrollmentModel,
        FinancialTransactionModel,
        ParentProfileModel,
        RoleModel,
        SessionModel,
        StudentProfileModel,
        SyllabusItemModel,
        TeacherProfileModel,
        UserModel,
    )

    stats = {
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
    }

    used_national_ids: set[str] = set()
    used_logins: set[str] = set()

    def _new_nid():
        while True:
            nid = _national_id()
            if nid not in used_national_ids:
                used_national_ids.add(nid)
                return nid

    def _new_login(prefix, idx):
        login = f"{prefix}{idx}"
        while login in used_logins:
            idx += 1
            login = f"{prefix}{idx}"
        used_logins.add(login)
        return login, idx

    # ── Roles ──
    for role_name in ("ADMIN", "TEACHER", "STUDENT", "PARENT"):
        if not RoleModel.query.get(role_name):
            db.session.add(RoleModel(name=role_name))
    db.session.flush()

    # ── Admin ──
    admin = UserModel.query.filter_by(login="admin").first()
    if admin is None:
        admin = UserModel(login="admin")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.flush()
        admin.roles.append(RoleModel.query.get("ADMIN"))
        stats["users"] += 1
    used_logins.add("admin")

    # ── Teachers ──
    teachers = []
    teacher_idx = 1
    for first, last in TEACHER_NAMES:
        login, teacher_idx = _new_login("teacher", teacher_idx)
        user = UserModel(login=login)
        user.set_password("teacher123")
        db.session.add(user)
        db.session.flush()
        user.roles.append(RoleModel.query.get("TEACHER"))
        profile = TeacherProfileModel(
            user_id=user.id,
            first_name=first,
            last_name=last,
            national_id=_new_nid(),
            mobile_phone=_phone(),
        )
        db.session.add(profile)
        teachers.append(user)
        stats["users"] += 1

    # ── Students ──
    students = []
    student_idx = 1
    for i in range(30):
        is_female = random.random() < 0.45
        first = _pick(
            PERSIAN_FEMALE_FIRST_NAMES if is_female else PERSIAN_MALE_FIRST_NAMES
        )
        last = _pick(PERSIAN_LAST_NAMES)
        login, student_idx = _new_login("student", student_idx)
        user = UserModel(login=login)
        user.set_password("student123")
        db.session.add(user)
        db.session.flush()
        user.roles.append(RoleModel.query.get("STUDENT"))
        birth_year = random.randint(2006, 2012)
        profile = StudentProfileModel(
            user_id=user.id,
            first_name=first,
            last_name=last,
            national_id=_new_nid(),
            mobile_phone=_phone(),
            birth_date=date(birth_year, random.randint(1, 12), random.randint(1, 28)),
            gender="FEMALE" if is_female else "MALE",
        )
        db.session.add(profile)
        students.append(user)
        stats["users"] += 1

    # ── Parents ──
    parents = []
    parent_idx = 1
    for i in range(5):
        is_female = random.random() < 0.3
        first = _pick(
            PERSIAN_FEMALE_FIRST_NAMES if is_female else PERSIAN_MALE_FIRST_NAMES
        )
        last = _pick(PERSIAN_LAST_NAMES)
        login, parent_idx = _new_login("parent", parent_idx)
        user = UserModel(login=login)
        user.set_password("parent123")
        db.session.add(user)
        db.session.flush()
        user.roles.append(RoleModel.query.get("PARENT"))
        profile = ParentProfileModel(
            user_id=user.id,
            first_name=first,
            last_name=last,
            national_id=_new_nid(),
            mobile_phone=_phone(),
        )
        db.session.add(profile)
        parents.append(user)
        stats["users"] += 1

    db.session.flush()

    # Link parents to students
    student_profiles = StudentProfileModel.query.all()
    for i, parent in enumerate(parents):
        parent_profile = ParentProfileModel.query.filter_by(user_id=parent.id).first()
        if parent_profile and i * 6 < len(student_profiles):
            target = student_profiles[i * 6]
            if target not in parent_profile.children:
                parent_profile.children.append(target)

    # ── Courses ──
    courses = []
    for title, desc, num_s, min_age, max_age in COURSES:
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
                    description=f"توضیحات فصل {j}",
                )
            )
        courses.append(course)
        stats["courses"] += 1

    db.session.flush()

    # ── Classes ──
    classes = []
    today = date.today()
    start = today - timedelta(days=30)

    # Create some overlapping classes for conflict testing
    # Class 0 (math group A) and Class 3 (english group A) will have same Saturday slot
    conflict_course = courses[0]  # Math
    conflict_course2 = courses[3]  # English

    academy_class = AcademyClassModel(
        course_id=conflict_course.id,
        title=f"{conflict_course.title} - گروه الف",
        start_date=start,
        end_date=start + timedelta(days=90),
        capacity=15,
        num_sessions=conflict_course.num_sessions,
        tuition=450000,
        status="ACTIVE",
        teacher_user_id=teachers[0].id,
    )
    db.session.add(academy_class)
    db.session.flush()

    db.session.add(
        ClassScheduleModel(
            class_id=academy_class.id,
            weekday="SATURDAY",
            start_time=time(8, 0),
            end_time=time(10, 0),
        )
    )
    db.session.add(
        ClassScheduleModel(
            class_id=academy_class.id,
            weekday="MONDAY",
            start_time=time(8, 0),
            end_time=time(10, 0),
        )
    )
    classes.append(academy_class)
    stats["classes"] += 1

    # Conflict class (same Saturday 8-10 slot)
    conflict_class = AcademyClassModel(
        course_id=conflict_course2.id,
        title=f"{conflict_course2.title} - گروه الف",
        start_date=start,
        end_date=start + timedelta(days=90),
        capacity=12,
        num_sessions=conflict_course2.num_sessions,
        tuition=550000,
        status="ACTIVE",
        teacher_user_id=teachers[1].id,
    )
    db.session.add(conflict_class)
    db.session.flush()

    db.session.add(
        ClassScheduleModel(
            class_id=conflict_class.id,
            weekday="SATURDAY",
            start_time=time(8, 0),
            end_time=time(10, 0),
        )
    )
    db.session.add(
        ClassScheduleModel(
            class_id=conflict_class.id,
            weekday="THURSDAY",
            start_time=time(14, 0),
            end_time=time(16, 0),
        )
    )
    classes.append(conflict_class)
    stats["classes"] += 1

    # Other classes with varied schedules
    for ci in range(2, 5):
        course = courses[ci % len(courses)]
        teacher = teachers[ci % len(teachers)]
        sched = WEEKDAY_SCHEDULES[ci % len(WEEKDAY_SCHEDULES)]

        cls = AcademyClassModel(
            course_id=course.id,
            title=f"{course.title} - {CLASS_TITLES[ci % len(CLASS_TITLES)]}",
            start_date=start,
            end_date=start + timedelta(days=90),
            capacity=random.randint(10, 25),
            num_sessions=course.num_sessions,
            tuition=random.choice([350000, 400000, 500000, 600000]),
            status="ACTIVE",
            teacher_user_id=teacher.id,
        )
        db.session.add(cls)
        db.session.flush()

        for wd, sh, sm, eh, em in sched:
            db.session.add(
                ClassScheduleModel(
                    class_id=cls.id,
                    weekday=wd,
                    start_time=time(sh, sm),
                    end_time=time(eh, em),
                )
            )

        classes.append(cls)
        stats["classes"] += 1

    db.session.flush()

    # ── Sessions ──
    for cls in classes:
        sched_entries = ClassScheduleModel.query.filter_by(class_id=cls.id).all()
        if not sched_entries:
            continue

        session_date = cls.start_date
        sessions_created = 0
        while sessions_created < cls.num_sessions:
            for sched in sched_entries:
                if sessions_created >= cls.num_sessions:
                    break
                # Find next occurrence of this weekday
                while session_date.weekday() != [
                    "SATURDAY",
                    "SUNDAY",
                    "MONDAY",
                    "TUESDAY",
                    "WEDNESDAY",
                    "THURSDAY",
                    "FRIDAY",
                ].index(sched.weekday):
                    session_date += timedelta(days=1)

                sessions_created += 1
                is_past = session_date < today
                status = "COMPLETED" if is_past else "SCHEDULED"
                if is_past and random.random() < 0.1:
                    status = "CANCELLED"

                db.session.add(
                    SessionModel(
                        class_id=cls.id,
                        session_number=sessions_created,
                        scheduled_date=session_date,
                        start_time=sched.start_time,
                        end_time=sched.end_time,
                        status=status,
                        title=f"جلسه {sessions_created}",
                    )
                )
                session_date += timedelta(days=1)
                stats["sessions"] += 1

    db.session.flush()

    # ── Enrollments ──
    # Enroll most students in class 0, some in class 1 (with conflicts), rest scattered
    enrolled_pairs: set[tuple[int, int]] = set()

    # Enroll first 15 students in class 0 (no conflict)
    for s in students[:15]:
        if (s.id, classes[0].id) not in enrolled_pairs:
            enrollment = EnrollmentModel(
                student_user_id=s.id,
                class_id=classes[0].id,
                status="APPROVED",
                requested_at=datetime.now() - timedelta(days=random.randint(5, 25)),
                approved_at=datetime.now() - timedelta(days=random.randint(1, 20)),
            )
            db.session.add(enrollment)
            enrolled_pairs.add((s.id, classes[0].id))
            stats["enrollments"] += 1

    # Enroll first 5 students in class 1 (conflicts with class 0!)
    for s in students[:5]:
        if (s.id, classes[1].id) not in enrolled_pairs:
            enrollment = EnrollmentModel(
                student_user_id=s.id,
                class_id=classes[1].id,
                status="APPROVED",
                requested_at=datetime.now() - timedelta(days=random.randint(5, 25)),
                approved_at=datetime.now() - timedelta(days=random.randint(1, 20)),
            )
            db.session.add(enrollment)
            enrolled_pairs.add((s.id, classes[1].id))
            stats["enrollments"] += 1

    # Enroll remaining students in other classes
    for i, s in enumerate(students[15:]):
        target_class = classes[(i % (len(classes) - 2)) + 2]
        if (s.id, target_class.id) not in enrolled_pairs:
            status = "APPROVED" if random.random() < 0.8 else "PENDING"
            enrollment = EnrollmentModel(
                student_user_id=s.id,
                class_id=target_class.id,
                status=status,
                requested_at=datetime.now() - timedelta(days=random.randint(5, 25)),
                approved_at=datetime.now() - timedelta(days=random.randint(1, 20))
                if status == "APPROVED"
                else None,
            )
            db.session.add(enrollment)
            enrolled_pairs.add((s.id, target_class.id))
            stats["enrollments"] += 1

    db.session.flush()

    # ── Attendance ──
    enrollments = EnrollmentModel.query.filter_by(status="APPROVED").all()
    for enrollment in enrollments:
        sessions = SessionModel.query.filter_by(
            class_id=enrollment.class_id, status="COMPLETED"
        ).all()
        for session in sessions:
            if random.random() < 0.85:
                status = random.choices(
                    ["PRESENT", "ABSENT", "LATE", "EXCUSED"],
                    weights=[70, 15, 10, 5],
                )[0]
                db.session.add(
                    AttendanceModel(
                        enrollment_id=enrollment.id,
                        session_id=session.id,
                        status=status,
                        recorded_by=teachers[0].id if teachers else admin.id,
                    )
                )
                stats["attendances"] += 1

    db.session.flush()

    # ── Activities ──
    activity_titles = [
        ("تمرین فصل اول", "HOMEWORK"),
        ("پروژه پایانی", "PROJECT"),
        ("آزمون کلاسی", "QUIZ"),
    ]

    for cls in classes[:3]:
        for title, atype in activity_titles:
            activity = ActivityModel(
                type=atype,
                title=title,
                description=f"توضیحات {title} - {cls.title}",
                requirement="REQUIRED",
                max_score=100,
                class_id=cls.id,
            )
            db.session.add(activity)
            stats["activities"] += 1

    db.session.flush()

    # ── Activity Submissions ──
    activities = ActivityModel.query.all()
    for activity in activities:
        class_enrollments = EnrollmentModel.query.filter_by(
            class_id=activity.class_id, status="APPROVED"
        ).all()
        for enrollment in class_enrollments[
            : random.randint(2, min(5, len(class_enrollments)))
        ]:
            status = random.choices(
                ["GRADED", "SUBMITTED", "NOT_SUBMITTED"],
                weights=[50, 30, 20],
            )[0]
            score = random.randint(50, 100) if status == "GRADED" else None
            from app.infrastructure.database.models import ActivitySubmissionModel

            submission = ActivitySubmissionModel(
                activity_id=activity.id,
                student_user_id=enrollment.student_user_id,
                enrollment_id=enrollment.id,
                text_content=f"پاسخ تکلیف {activity.title}",
                submitted_at=datetime.now() - timedelta(days=random.randint(1, 10))
                if status != "NOT_SUBMITTED"
                else None,
                status=status,
                score=score,
                graded_at=datetime.now() - timedelta(days=random.randint(0, 5))
                if status == "GRADED"
                else None,
                graded_by=teachers[0].id if teachers and status == "GRADED" else None,
            )
            db.session.add(submission)
            stats["submissions"] += 1

    db.session.flush()

    # ── Assessments ──
    assessment_data = [
        ("آزمون میان‌ترم", "MIDTERM", 20, 10),
        ("آزمون پایانی", "FINAL_EXAM", 30, 15),
        ("آزمون کلاسی", "QUIZ", 10, 5),
    ]

    for cls in classes[:3]:
        for title, atype, max_s, pass_s in assessment_data:
            if random.random() < 0.6:
                assessment = AssessmentModel(
                    class_id=cls.id,
                    type=atype,
                    title=title,
                    description=f"{title} - {cls.title}",
                    scheduled_date=today + timedelta(days=random.randint(-15, 30)),
                    max_score=max_s,
                    passing_score=pass_s,
                    status=random.choice(
                        ["DRAFT", "SCHEDULED", "OPEN", "CLOSED", "GRADED"]
                    ),
                    created_by=teachers[0].id if teachers else admin.id,
                )
                db.session.add(assessment)
                stats["assessments"] += 1

    db.session.flush()

    # ── Assessment Results ──
    assessments = AssessmentModel.query.filter(
        AssessmentModel.status.in_(["CLOSED", "GRADED"])
    ).all()
    for assessment in assessments:
        class_enrollments = EnrollmentModel.query.filter_by(
            class_id=assessment.class_id, status="APPROVED"
        ).all()
        for enrollment in class_enrollments:
            score = random.uniform(
                float(assessment.passing_score) * 0.5,
                float(assessment.max_score),
            )
            passed = score >= float(assessment.passing_score)
            db.session.add(
                AssessmentResultModel(
                    assessment_id=assessment.id,
                    enrollment_id=enrollment.id,
                    student_user_id=enrollment.student_user_id,
                    score=round(score, 1),
                    max_score=assessment.max_score,
                    percentage=round(score / float(assessment.max_score) * 100, 1),
                    result_status="GRADED",
                    pass_fail="PASS" if passed else "FAIL",
                    graded_by=teachers[0].id if teachers else admin.id,
                    graded_at=datetime.now() - timedelta(days=random.randint(0, 10)),
                )
            )
            stats["results"] += 1

    db.session.flush()

    # ── Financial Transactions ──
    for enrollment in enrollments:
        cls = AcademyClassModel.query.get(enrollment.class_id)
        if cls is None or cls.tuition <= 0:
            continue

        # Tuition charge
        charge = FinancialTransactionModel(
            student_user_id=enrollment.student_user_id,
            amount=cls.tuition,
            transaction_type="CHARGE",
            category="TUITION",
            description=f"شهریه {cls.title}",
            class_id=cls.id,
            enrollment_id=enrollment.id,
            created_by=admin.id,
        )
        db.session.add(charge)
        stats["transactions"] += 1

        # Random payments (exact Decimal math: binary floats would store
        # artifacts like 135000.00000000001 in Numeric columns)
        if random.random() < 0.7:
            paid = int(
                Decimal(str(cls.tuition))
                * random.choice([Decimal("1.0"), Decimal("0.5"), Decimal("0.3")])
            )
            db.session.add(
                FinancialTransactionModel(
                    student_user_id=enrollment.student_user_id,
                    amount=paid,
                    transaction_type="PAYMENT",
                    category="TUITION",
                    description=f"پرداخت شهریه {cls.title}",
                    payment_method=random.choice(["CASH", "CARD", "BANK_TRANSFER"]),
                    class_id=cls.id,
                    enrollment_id=enrollment.id,
                    created_by=admin.id,
                )
            )
            stats["transactions"] += 1

        # Occasional discount (exact Decimal math, whole Toman)
        if random.random() < 0.15:
            discount = int(
                Decimal(str(cls.tuition))
                * Decimal(str(random.uniform(0.05, 0.2)))
            )
            db.session.add(
                FinancialTransactionModel(
                    student_user_id=enrollment.student_user_id,
                    amount=round(discount, 0),
                    transaction_type="DISCOUNT",
                    category="TUITION",
                    description=f"تخفیف شهریه {cls.title}",
                    class_id=cls.id,
                    enrollment_id=enrollment.id,
                    created_by=admin.id,
                )
            )
            stats["transactions"] += 1

    db.session.commit()

    return stats
