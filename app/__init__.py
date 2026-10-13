import os

import click
from flask import Flask, jsonify, render_template
from flask_login import LoginManager

from app.extensions import db as db  # noqa: F401
from app.extensions import init_db
from config import config

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "error"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Secrets that must never sign production sessions/CSRF tokens.
_REJECTED_PRODUCTION_SECRETS = frozenset(
    {"", "change-me", "changeme", "secret", "password", "development", "test"}
)


def _reject_insecure_production_secret(app) -> None:
    """Refuse to boot production on a missing/default/weak SECRET_KEY.

    A public default would let anyone forge session cookies and CSRF tokens.
    The secret value itself is never included in the error. Development and
    testing configs keep their convenient fallback (with a warning).
    """
    secret = app.config.get("SECRET_KEY") or ""
    if not secret or secret.strip().lower() in _REJECTED_PRODUCTION_SECRETS:
        raise RuntimeError(
            "Refusing to start in production: SECRET_KEY is missing or uses a "
            "known-default value. Set a strong random SECRET_KEY environment variable."
        )
    if len(secret) < 32:
        # Warn only: refusing here could break deployments whose existing
        # secret predates this check. Rotate to >= 32 characters.
        app.logger.warning(
            "SECRET_KEY is shorter than 32 characters; "
            "use a strong random value of at least 32 characters."
        )


def create_app(config_name="development"):
    """Application factory."""
    app = Flask(
        __name__,
        template_folder=os.path.join(PROJECT_ROOT, "templates"),
        static_folder=os.path.join(PROJECT_ROOT, "static"),
    )
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    if config_name == "production":
        _reject_insecure_production_secret(app)

    _register_extensions(app)
    _register_blueprints(app)
    _register_routes(app)
    _register_cli(app)
    _register_security_headers(app)

    if (
        config_name != "testing"
        and os.environ.get("ENABLE_SCHEDULER", "").lower() == "true"
    ):
        from app.scheduler import start_scheduler

        start_scheduler(app, interval_seconds=3600)

    return app


def _register_extensions(app):
    """Register Flask extensions."""
    init_db(app)
    login_manager.init_app(app)

    from flask_wtf.csrf import CSRFProtect

    CSRFProtect(app)

    app.jinja_env.globals["any"] = any
    app.jinja_env.globals["all"] = all

    from app.infrastructure.database.models import UserModel

    @login_manager.user_loader
    def load_user(user_id: str):
        return UserModel.query.get(int(user_id))

    from app.infrastructure.notification.registry import init_default_providers

    init_default_providers()


def _register_blueprints(app):
    """Register Flask blueprints."""
    from app.interface.web import web_bp
    from app.interface.web.academy.routes import academy_bp
    from app.interface.web.activity.routes import activity_bp
    from app.interface.web.admin.routes import admin_bp
    from app.interface.web.assessment.routes import assessment_bp
    from app.interface.web.attendance.routes import attendance_bp
    from app.interface.web.auth import auth_bp
    from app.interface.web.enrollment.routes import enrollment_bp
    from app.interface.web.file_management.routes import file_bp
    from app.interface.web.finance.routes import finance_bp
    from app.interface.web.notification.routes import notification_bp
    from app.interface.web.portal.routes import portal_bp
    from app.interface.web.public.routes import public_bp
    from app.interface.web.reporting.routes import reporting_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(academy_bp)
    app.register_blueprint(enrollment_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(activity_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(assessment_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(reporting_bp)
    app.register_blueprint(file_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(public_bp)


def _register_routes(app):
    """Register application-wide routes and template filters/globals."""

    @app.route("/health")
    def health():
        # Process liveness plus critical dependency (database) status.
        # 200 = serving; 503 = process alive but database unreachable.
        # No secrets, credentials, or record counts are exposed here.
        from sqlalchemy import text as sa_text

        from app.extensions import db

        try:
            db.session.execute(sa_text("SELECT 1"))
        except Exception:
            return jsonify({"status": "degraded", "database": "error"}), 503
        return jsonify({"status": "ok", "database": "ok"})

    @app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/400.html"), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    _register_template_filters(app)


def _register_security_headers(app) -> None:
    """Baseline response hardening (defense in depth behind the proxy).

    SAMEORIGIN framing (CSRF tokens already protect state-changing forms),
    nosniff (blocks MIME-sniffing of user-uploaded content served inline),
    and a conservative referrer policy. HSTS is deliberately NOT set here:
    TLS is terminated upstream and HSTS is an infrastructure decision.
    """

    @app.after_request
    def _apply_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "no-referrer-when-downgrade")
        return response


def _register_template_filters(app):
    """Register Jinja template filters and globals for Persian date display."""
    from app.utils.date_utils import (
        format_jalali,
        format_jalali_date_input,
        format_jalali_datetime,
        format_jalali_time,
    )

    @app.template_filter("jalali")
    def jalali_filter(d):
        """Format a date/datetime as Jalali date string."""
        return format_jalali(d)

    @app.template_filter("jalali_datetime")
    def jalali_datetime_filter(dt):
        """Format a datetime as Jalali date + time string."""
        return format_jalali_datetime(dt)

    @app.template_filter("jalali_time")
    def jalali_time_filter(t):
        """Format a time as HH:MM."""
        return format_jalali_time(t)

    @app.template_filter("to_jalali")
    def to_jalali_filter(d, fmt="%Y/%m/%d"):
        """Generic Jalali format filter with customizable format."""
        return format_jalali(d, fmt)

    @app.template_filter("to_jalali_input")
    def to_jalali_input_filter(d):
        """Format a date for use in form inputs (Jalali YYYY/MM/DD)."""
        return format_jalali_date_input(d)

    @app.template_filter("currency")
    def currency_filter(amount):
        """Format a number as Toman currency (exact Decimal math)."""
        if amount is None:
            return "—"
        try:
            from decimal import Decimal, InvalidOperation

            val = amount if isinstance(amount, Decimal) else Decimal(str(amount))
            return f"{val.quantize(Decimal('1')):,} تومان"
        except InvalidOperation:
            # Single-exception clause on purpose: ruff 0.17's formatter
            # corrupts bare multi-exception tuples into invalid syntax.
            return str(amount)

    @app.template_filter("persian_label")
    def persian_label_filter(value):
        """Translate enum/status values to Persian labels."""
        labels = {
            "PENDING": "در انتظار",
            "APPROVED": "تأیید شده",
            "ACTIVE": "فعال",
            "REJECTED": "رد شده",
            "CANCELLED": "لغو شده",
            "COMPLETED": "تکمیل شده",
            "PLANNED": "برنامه‌ریزی شده",
            "SCHEDULED": "برنامه‌ریزی شده",
            "DRAFT": "پیش‌نویس",
            "OPEN": "باز",
            "CLOSED": "بسته شده",
            "GRADED": "نمره‌گذاری شده",
            "NOT_GRADED": "نمره‌گذاری نشده",
            "PRESENT": "حاضر",
            "ABSENT": "غایب",
            "LATE": "تاخیر",
            "EXCUSED": "معذور",
            "REQUIRED": "الزامی",
            "OPTIONAL": "اختیاری",
            "SUBMITTED": "ارسال شده",
            "NOT_SUBMITTED": "ارسال نشده",
            "RETURNED": "برگشت داده شده",
            "PASS": "قبول",
            "FAIL": "مردود",
            "NOT_DETERMINED": "تعیین نشده",
            "PAYMENT": "پرداخت",
            "CHARGE": "هزینه",
            "DISCOUNT": "تخفیف",
            "REFUND": "بازپرداخت",
            "ADJUSTMENT": "اصلاح حساب",
            "CORRECTED": "تصحیح شده",
            "REVERSAL": "ابطال",
            "VOIDED": "باطل شده",
            "TUITION": "شهریه",
            "BOOK": "کتاب",
            "EQUIPMENT": "تجهیزات",
            "EXAM": "آزمون",
            "CASH": "نقدی",
            "CARD": "کارت",
            "BANK_TRANSFER": "انتقال بانکی",
            "ONLINE": "آنلاین",
            "MALE": "پسر",
            "FEMALE": "دختر",
            "HOMEWORK": "تکلیف",
            "QUIZ": "آزمون کلاسی",
            "PROJECT": "پروژه",
            "PRACTICE": "تمرین",
            "FINAL_EXAM": "آزمون پایانی",
            "MIDTERM": "آزمون میان‌ترم",
            "PRACTICAL": "عملی",
            "ORAL": "شفاهی",
            "OTHER": "سایر",
            "SMS": "پیامک",
            "TELEGRAM": "تلگرام",
            "BALE": "بله",
            "EMAIL": "ایمیل",
            "IN_APP": "در برنامه",
            "SATURDAY": "شنبه",
            "SUNDAY": "یکشنبه",
            "MONDAY": "دوشنبه",
            "TUESDAY": "سه‌شنبه",
            "WEDNESDAY": "چهارشنبه",
            "THURSDAY": "پنجشنبه",
            "FRIDAY": "جمعه",
            "UNREAD": "خوانده نشده",
            "READ": "خوانده شده",
            "SENT": "ارسال شده",
            "FAILED": "ناموفق",
            "DELETED": "حذف شده",
        }
        return labels.get(str(value), str(value))

    @app.template_filter("status_badge")
    def status_badge_filter(value):
        """Render a transaction type as a Persian label with badge CSS class."""
        from markupsafe import Markup, escape

        label = persian_label_filter(value)
        # CSS class for badge color based on type
        type_class = {
            "PAYMENT": "success",
            "DISCOUNT": "info",
            "CHARGE": "warning",
            "REFUND": "danger",
            "ADJUSTMENT": "secondary",
            "REVERSAL": "dark",
        }.get(str(value), "secondary")
        # Wrapper is server-generated markup; the label itself is escaped so
        # an unexpected stored value cannot inject HTML.
        return Markup(f'<span class="badge badge-{type_class}">{escape(label)}</span>')

    # Also exposed as a global: 100+ templates call status_badge(...) as a
    # bare name, which Jinja resolves through the context (not the filter
    # table, which only the pipe syntax uses). Without this, every
    # transaction list with at least one row 500s.
    app.jinja_env.globals["status_badge"] = status_badge_filter

    @app.template_filter("weekday_fa")
    def weekday_filter(value):
        """Translate weekday name to Persian."""
        return persian_label_filter(value)


def _register_cli(app):
    """Register Flask CLI commands."""
    import time

    @app.cli.command("seed")
    def seed_command():
        """Seed the database with initial test data.

        Creates roles, 4 test users (admin, teacher, student, parent),
        profiles, and links parent1 to student1.
        Idempotent: running twice does not create duplicates.

        DEVELOPMENT/TESTING ONLY: refuses to run when FLASK_ENV=production
        so documented weak credentials (admin/admin123, …) can never be
        created on a real installation. Use `flask create-admin` there.
        """
        import os

        if os.environ.get("FLASK_ENV", "").lower() == "production":
            raise click.ClickException(
                "Refusing to seed a production database with test credentials. "
                "Use `flask create-admin` instead."
            )
        from datetime import date

        from app.extensions import db
        from app.infrastructure.database.models import (
            AcademyClassModel,
            ActivityModel,
            AssessmentModel,
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

        # Ensure roles exist
        for role_name in ("ADMIN", "TEACHER", "STUDENT", "PARENT"):
            if not RoleModel.query.get(role_name):
                db.session.add(RoleModel(name=role_name))
        db.session.flush()

        # Admin
        admin = UserModel.query.filter_by(login="admin").first()
        if admin is None:
            admin = UserModel(login="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.flush()
            admin_role = RoleModel.query.get("ADMIN")
            admin.roles.append(admin_role)
            print("  Created: admin / admin123")
        else:
            print("  Already exists: admin")

        # Teacher
        teacher = UserModel.query.filter_by(login="teacher1").first()
        if teacher is None:
            teacher = UserModel(login="teacher1")
            teacher.set_password("teacher123")
            db.session.add(teacher)
            db.session.flush()
            teacher_role = RoleModel.query.get("TEACHER")
            teacher.roles.append(teacher_role)
            profile = TeacherProfileModel(
                user_id=teacher.id,
                first_name="Mohammad",
                last_name="Ahmadi",
                national_id="9876543210",
                mobile_phone="09129876543",
            )
            db.session.add(profile)
            print("  Created: teacher1 / teacher123")
        else:
            print("  Already exists: teacher1")

        # Student
        student = UserModel.query.filter_by(login="student1").first()
        if student is None:
            student = UserModel(login="student1")
            student.set_password("student123")
            db.session.add(student)
            db.session.flush()
            student_role = RoleModel.query.get("STUDENT")
            student.roles.append(student_role)
            profile = StudentProfileModel(
                user_id=student.id,
                first_name="Ali",
                last_name="Rezaei",
                national_id="1234567890",
                mobile_phone="09121234567",
                birth_date=date(2008, 5, 15),
                gender="MALE",
            )
            db.session.add(profile)
            print("  Created: student1 / student123")
        else:
            print("  Already exists: student1")

        # Parent
        parent = UserModel.query.filter_by(login="parent1").first()
        if parent is None:
            parent = UserModel(login="parent1")
            parent.set_password("parent123")
            db.session.add(parent)
            db.session.flush()
            parent_role = RoleModel.query.get("PARENT")
            parent.roles.append(parent_role)
            parent_profile = ParentProfileModel(
                user_id=parent.id,
                first_name="Reza",
                last_name="Rezaei",
                national_id="1122334455",
                mobile_phone="09112233445",
            )
            db.session.add(parent_profile)
            db.session.flush()

            # Link parent to student
            student_profile = StudentProfileModel.query.filter_by(
                user_id=student.id
            ).first()
            if student_profile and student_profile not in parent_profile.children:
                parent_profile.children.append(student_profile)
            print("  Created: parent1 / parent123 (linked to student1)")
        else:
            # Ensure parent-student link exists
            parent_profile = ParentProfileModel.query.filter_by(
                user_id=parent.id
            ).first()
            student_profile = StudentProfileModel.query.filter_by(
                user_id=student.id
            ).first()
            if parent_profile and student_profile:
                if student_profile not in parent_profile.children:
                    parent_profile.children.append(student_profile)
                    print("  Linked parent1 to student1")
                else:
                    print("  Already exists: parent1")
            else:
                print("  Already exists: parent1")

        # ── Course ───────────────────────────────────────────────────────
        course = CourseModel.query.filter_by(title="ریاضی کنکور").first()
        if course is None:
            course = CourseModel(
                title="ریاضی کنکور",
                description="دوره جامع ریاضی کنکور شامل جبر، هندسه و آمار",
                num_sessions=10,
                min_age=16,
                max_age=19,
                prerequisites="ریاضی پایه",
            )
            db.session.add(course)
            db.session.flush()
            print("  Created: course (ریاضی کنکور)")

            for i, title in enumerate(
                [
                    "مقدمه جبر",
                    "معادلات درجه دوم",
                    "هندسه تحلیلی",
                    "احتمال و آمار",
                    "ترکیبات",
                ],
                start=1,
            ):
                db.session.add(
                    SyllabusItemModel(
                        course_id=course.id,
                        order=i,
                        title=title,
                        description=f"توضیحات {title}",
                    )
                )
            print("  Created: 5 syllabus items")
        else:
            print("  Already exists: course (ریاضی کنکور)")

        # ── Class ────────────────────────────────────────────────────────
        academy_class = AcademyClassModel.query.filter_by(title="کلاس رضا").first()
        if academy_class is None:
            from datetime import time as _time

            academy_class = AcademyClassModel(
                course_id=course.id,
                title="کلاس رضا",
                start_date=date(2026, 9, 1),
                end_date=date(2026, 11, 30),
                capacity=25,
                num_sessions=5,
                tuition=500000,
                status="ACTIVE",
                teacher_user_id=teacher.id,
            )
            db.session.add(academy_class)
            db.session.flush()

            db.session.add(
                ClassScheduleModel(
                    class_id=academy_class.id,
                    weekday="SATURDAY",
                    start_time=_time(10, 0),
                    end_time=_time(12, 0),
                )
            )
            db.session.add(
                ClassScheduleModel(
                    class_id=academy_class.id,
                    weekday="TUESDAY",
                    start_time=_time(10, 0),
                    end_time=_time(12, 0),
                )
            )
            db.session.flush()
            print("  Created: class (کلاس رضا) + schedule")
        else:
            print("  Already exists: class (کلاس رضا)")

        # ── Sessions ─────────────────────────────────────────────────────
        existing_session = SessionModel.query.filter_by(
            class_id=academy_class.id
        ).first()
        if existing_session is None:
            from datetime import time as _time

            session_dates = [
                date(2026, 9, 5),
                date(2026, 9, 8),
                date(2026, 9, 12),
                date(2026, 9, 15),
                date(2026, 9, 19),
            ]
            for i, sdate in enumerate(session_dates, start=1):
                db.session.add(
                    SessionModel(
                        class_id=academy_class.id,
                        session_number=i,
                        scheduled_date=sdate,
                        start_time=_time(10, 0),
                        end_time=_time(12, 0),
                        status="COMPLETED" if i <= 2 else "SCHEDULED",
                        title=f"جلسه {i}",
                    )
                )
            db.session.flush()
            print("  Created: 5 sessions")
        else:
            print("  Already exists: sessions")

        # ── Enrollment ───────────────────────────────────────────────────
        enrollment = EnrollmentModel.query.filter_by(
            student_user_id=student.id, class_id=academy_class.id
        ).first()
        if enrollment is None:
            from datetime import datetime as _dt

            enrollment = EnrollmentModel(
                student_user_id=student.id,
                class_id=academy_class.id,
                status="APPROVED",
                requested_at=_dt(2026, 8, 25),
                approved_at=_dt(2026, 8, 26),
            )
            db.session.add(enrollment)
            db.session.flush()
            print("  Created: enrollment (student1 -> کلاس رضا)")
        else:
            print("  Already exists: enrollment (student1 -> کلاس رضا)")

        # ── Activity ─────────────────────────────────────────────────────
        existing_activity = ActivityModel.query.filter_by(
            class_id=academy_class.id, title="تمرین فصل اول"
        ).first()
        if existing_activity is None:
            db.session.add(
                ActivityModel(
                    type="HOMEWORK",
                    title="تمرین فصل اول",
                    description="تمرین‌های فصل اول جبر - حل مسائل صفحه ۴۵ تا ۵۰",
                    requirement="REQUIRED",
                    max_score=100,
                    class_id=academy_class.id,
                )
            )
            db.session.flush()
            print("  Created: activity (تمرین فصل اول)")
        else:
            print("  Already exists: activity (تمرین فصل اول)")

        # ── Assessment ───────────────────────────────────────────────────
        existing_assessment = AssessmentModel.query.filter_by(
            class_id=academy_class.id, title="آزمون میان‌ترم"
        ).first()
        if existing_assessment is None:
            db.session.add(
                AssessmentModel(
                    class_id=academy_class.id,
                    type="MIDTERM",
                    title="آزمون میان‌ترم",
                    description="آزمون میان‌ترم ریاضی کنکور",
                    scheduled_date=date(2026, 10, 15),
                    max_score=20,
                    passing_score=10,
                    status="SCHEDULED",
                    created_by=teacher.id,
                )
            )
            db.session.flush()
            print("  Created: assessment (آزمون میان‌ترم)")
        else:
            print("  Already exists: assessment (آزمون میان‌ترم)")

        # ── Finance ──────────────────────────────────────────────────────
        existing_charge = FinancialTransactionModel.query.filter_by(
            student_user_id=student.id,
            category="TUITION",
            class_id=academy_class.id,
        ).first()
        if existing_charge is None:
            db.session.add(
                FinancialTransactionModel(
                    student_user_id=student.id,
                    amount=500000,
                    transaction_type="CHARGE",
                    category="TUITION",
                    description="شهریه کلاس رضا",
                    class_id=academy_class.id,
                    enrollment_id=enrollment.id,
                    created_by=admin.id,
                )
            )
            db.session.flush()
            print("  Created: tuition charge for student1")
        else:
            print("  Already exists: tuition charge")

        db.session.commit()
        print("\nSeed completed successfully.")

    @app.cli.command("run-scheduler")
    def run_scheduler_command():
        """Start the background scheduler (blocks until interrupted).

        Runs automated daily and weekly jobs in a loop.
        """
        import signal
        import sys

        from app.scheduler import start_scheduler, stop_scheduler

        def _shutdown(sig, frame):
            print("\nShutting down scheduler...")
            stop_scheduler()
            sys.exit(0)

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        print("Starting scheduler (Ctrl+C to stop)...")
        start_scheduler(app, interval_seconds=3600)

        # Keep the main thread alive
        try:
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):  # fmt: skip
            stop_scheduler()

    @app.cli.command("run-jobs")
    def run_jobs_command():
        """Run all scheduled jobs once immediately (for testing/debugging)."""
        from app.scheduler import run_jobs_now

        print("Running scheduled jobs...")
        results = run_jobs_now()
        for job, result in results.items():
            print(f"  {job}: {result}")
        print("Done.")

    @app.cli.command("seed-demo")
    def seed_demo_command():
        """Generate rich demo data for product demonstrations.

        Creates: admin, 3 teachers, 30 students, 5 parents,
        4 courses, 5 classes with schedules, enrollments,
        sessions, attendance, activities, submissions,
        assessments, results, and financial transactions.

        DEVELOPMENT/TESTING ONLY: refuses to run when FLASK_ENV=production.
        """
        import os

        if os.environ.get("FLASK_ENV", "").lower() == "production":
            raise click.ClickException(
                "Refusing to seed a production database with demo data. "
                "Use `flask create-admin` instead."
            )
        from app.extensions import db
        from app.seed_demo import seed_demo_data

        print("Generating rich demo data...")
        stats = seed_demo_data(db)

        print("\n✓ Demo data generated successfully!")
        print(f"  Users:      {stats['users']}")
        print(f"  Courses:    {stats['courses']}")
        print(f"  Classes:    {stats['classes']}")
        print(f"  Enrollments:{stats['enrollments']}")
        print(f"  Sessions:   {stats['sessions']}")
        print(f"  Attendances:{stats['attendances']}")
        print(f"  Activities: {stats['activities']}")
        print(f"  Submissions:{stats['submissions']}")
        print(f"  Assessments:{stats['assessments']}")
        print(f"  Results:    {stats['results']}")
        print(f"  Transactions:{stats['transactions']}")
        print("\nTest credentials:")
        print("  admin / admin123")
        print("  teacher1 / teacher123")
        print("  student1 / student123")
        print("  parent1 / parent123")

    @app.cli.command("create-admin")
    @click.option(
        "--login", default="admin", show_default=True, help="Admin login name."
    )
    @click.option(
        "--password",
        default=None,
        help="Admin password (prompted securely via getpass if omitted).",
    )
    def create_admin_command(login, password):
        """Create the initial administrator account (safe for production).

        Unlike `flask seed`, this never creates documented weak credentials:
        the password is prompted without echo (or passed explicitly), must
        be at least 10 characters, and must not equal the login or a known
        default. Refuses to run if the login already exists. Prints the
        login only — never the password.
        """
        import getpass

        from app.application.auth.services import assign_role, create_user
        from app.infrastructure.database.models import UserModel

        if UserModel.query.filter_by(login=login).first() is not None:
            raise click.ClickException(f"Login {login!r} already exists.")

        if password is None:
            password = getpass.getpass(f"Password for {login}: ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                raise click.ClickException("Passwords do not match.")

        _validate_initial_admin_password(login, password)

        user = create_user(login, password)
        assign_role(user, "ADMIN")
        # Never print the password.
        print(f"Administrator {login!r} created.")


def _validate_initial_admin_password(login: str, password: str) -> None:
    """Enforce a strong initial-admin password (raises ValueError)."""
    import click

    weak = {"", "admin", "admin123", "password", "123456", "changeme", "change-me"}
    if (
        not password
        or len(password) < 10
        or password.strip().lower() in weak
        or password == login
    ):
        raise click.ClickException(
            "Password must be at least 10 characters and must not be the "
            "login name or a well-known default."
        )
