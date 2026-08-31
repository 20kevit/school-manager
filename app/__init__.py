import os

from flask import Flask, jsonify
from flask_login import LoginManager

from app.extensions import db as db  # noqa: F401
from app.extensions import init_db
from config import config

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "error"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app(config_name="development"):
    """Application factory."""
    app = Flask(
        __name__,
        template_folder=os.path.join(PROJECT_ROOT, "templates"),
        static_folder=os.path.join(PROJECT_ROOT, "static"),
    )
    app.config.from_object(config[config_name])

    _register_extensions(app)
    _register_blueprints(app)
    _register_routes(app)

    return app


def _register_extensions(app):
    """Register Flask extensions."""
    init_db(app)
    login_manager.init_app(app)

    from flask_wtf.csrf import CSRFProtect

    CSRFProtect(app)

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
    from app.interface.web.assessment.routes import assessment_bp
    from app.interface.web.attendance.routes import attendance_bp
    from app.interface.web.auth import auth_bp
    from app.interface.web.enrollment.routes import enrollment_bp
    from app.interface.web.file_management.routes import file_bp
    from app.interface.web.finance.routes import finance_bp
    from app.interface.web.notification.routes import notification_bp
    from app.interface.web.portal.routes import portal_bp
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


def _register_routes(app):
    """Register application-wide routes and template filters/globals."""

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(400)
    def bad_request(e):
        return "errors/400.html", 400

    @app.errorhandler(403)
    def forbidden(e):
        return "errors/403.html", 403

    @app.errorhandler(404)
    def not_found(e):
        return "errors/404.html", 404

    @app.errorhandler(500)
    def internal_error(e):
        return "errors/500.html", 500

    _register_template_filters(app)


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
        """Format a number as Toman currency."""
        if amount is None:
            return "—"
        try:
            val = float(amount)
            return f"{val:,.0f} تومان"
        except ValueError, TypeError:
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

    @app.template_filter("weekday_fa")
    def weekday_filter(value):
        """Translate weekday name to Persian."""
        return persian_label_filter(value)
