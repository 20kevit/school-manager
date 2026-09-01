"""Lightweight background scheduler for automated tasks.

Runs as a daemon thread started from the Flask app factory or via CLI.
No external dependencies (no Celery, no Redis, no APScheduler).
"""

from __future__ import annotations

import logging
import threading
from datetime import date, timedelta

logger = logging.getLogger(__name__)

_scheduler_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _daily_class_reminder_job() -> None:
    """Find sessions scheduled for tomorrow and send reminder notifications."""
    from app.application.notification.notification_service import (
        create_in_app_notification,
    )
    from app.domain.notification import NotificationType
    from app.infrastructure.database.models import (
        EnrollmentModel,
        SessionModel,
        UserModel,
    )

    tomorrow = date.today() + timedelta(days=1)

    sessions = SessionModel.query.filter(
        SessionModel.scheduled_date == tomorrow,
        SessionModel.status == "SCHEDULED",
    ).all()

    if not sessions:
        logger.info("No sessions scheduled for tomorrow (%s).", tomorrow)
        return

    sent_count = 0
    for session in sessions:
        academy_class = session.academy_class
        if academy_class is None:
            continue

        enrollments = EnrollmentModel.query.filter_by(
            class_id=session.class_id,
            status="APPROVED",
        ).all()

        for enrollment in enrollments:
            student = UserModel.query.get(enrollment.student_user_id)
            if student is None:
                continue

            class_title = academy_class.title
            start_time_str = (
                session.start_time.strftime("%H:%M") if session.start_time else ""
            )
            title = f"یادآوری کلاس: {class_title}"
            message = (
                f"یادآوری: کلاس {class_title} فردا ساعت {start_time_str} برگزار می‌شود."
            )

            try:
                create_in_app_notification(
                    user_id=enrollment.student_user_id,
                    title=title,
                    message=message,
                    notification_type=NotificationType.SESSION_REMINDER,
                    link=f"/portal/sessions/{session.id}",
                )
                sent_count += 1
            except Exception:
                logger.exception(
                    "Failed to send session reminder to user %s for session %s",
                    enrollment.student_user_id,
                    session.id,
                )

    logger.info(
        "Session reminder job completed: %d reminders sent for %d sessions.",
        sent_count,
        len(sessions),
    )


def _weekly_payment_reminder_job() -> None:
    """Find students with outstanding debt and send weekly reminders."""
    from sqlalchemy import func

    from app.application.notification.notification_service import (
        create_in_app_notification,
    )
    from app.domain.notification import NotificationType
    from app.extensions import db
    from app.infrastructure.database.models import (
        FinancialTransactionModel,
        StudentProfileModel,
        UserModel,
    )

    balances = (
        db.session.query(
            FinancialTransactionModel.student_user_id,
            func.sum(
                db.case(
                    (
                        FinancialTransactionModel.transaction_type == "PAYMENT",
                        FinancialTransactionModel.amount,
                    ),
                    (
                        FinancialTransactionModel.transaction_type == "DISCOUNT",
                        FinancialTransactionModel.amount,
                    ),
                    (
                        FinancialTransactionModel.transaction_type == "CHARGE",
                        -FinancialTransactionModel.amount,
                    ),
                    (
                        FinancialTransactionModel.transaction_type == "REFUND",
                        -FinancialTransactionModel.amount,
                    ),
                    (
                        FinancialTransactionModel.transaction_type == "REVERSAL",
                        FinancialTransactionModel.amount,
                    ),
                    (
                        FinancialTransactionModel.transaction_type == "ADJUSTMENT",
                        FinancialTransactionModel.amount,
                    ),
                    else_=0,
                )
            ),
        )
        .filter(FinancialTransactionModel.status == "ACTIVE")
        .group_by(FinancialTransactionModel.student_user_id)
        .having(
            func.sum(
                db.case(
                    (
                        FinancialTransactionModel.transaction_type == "PAYMENT",
                        FinancialTransactionModel.amount,
                    ),
                    (
                        FinancialTransactionModel.transaction_type == "DISCOUNT",
                        FinancialTransactionModel.amount,
                    ),
                    (
                        FinancialTransactionModel.transaction_type == "CHARGE",
                        -FinancialTransactionModel.amount,
                    ),
                    (
                        FinancialTransactionModel.transaction_type == "REFUND",
                        -FinancialTransactionModel.amount,
                    ),
                    (
                        FinancialTransactionModel.transaction_type == "REVERSAL",
                        FinancialTransactionModel.amount,
                    ),
                    (
                        FinancialTransactionModel.transaction_type == "ADJUSTMENT",
                        FinancialTransactionModel.amount,
                    ),
                    else_=0,
                )
            )
            < 0
        )
        .all()
    )

    if not balances:
        logger.info("No students with outstanding debt.")
        return

    sent_count = 0
    for student_user_id, balance in balances:
        student = UserModel.query.get(student_user_id)
        if student is None:
            continue

        profile = StudentProfileModel.query.filter_by(user_id=student_user_id).first()
        student_name = ""
        if profile:
            student_name = f"{profile.first_name} {profile.last_name}"

        debt_amount = abs(float(balance))
        title = "یادآوری پرداخت شهریه"
        message = (
            f"دانش‌آموز {student_name}، مبلغ {debt_amount:,.0f} تومان بدهی دارید. "
            "لطفاً نسبت به تسویه حساب اقدام فرمایید."
        )

        try:
            create_in_app_notification(
                user_id=student_user_id,
                title=title,
                message=message,
                notification_type=NotificationType.PAYMENT_RECEIVED,
                link="/portal/finance",
            )
            sent_count += 1
        except Exception:
            logger.exception(
                "Failed to send payment reminder to user %s", student_user_id
            )

    logger.info(
        "Payment reminder job completed: %d reminders sent to %d students.",
        sent_count,
        len(balances),
    )


def _run_scheduler_loop(interval_seconds: int = 3600) -> None:
    """Main scheduler loop that runs scheduled jobs.

    Runs once on startup (to catch anything missed while down),
    then every ``interval_seconds``.
    """
    from flask import current_app

    has_app = current_app is not None
    if not has_app:
        logger.warning("Scheduler running without Flask app context; skipping.")
        return

    last_daily_run: date | None = None
    last_weekly_run: date | None = None

    def _run_jobs() -> None:
        nonlocal last_daily_run, last_weekly_run

        today = date.today()

        # Daily class reminder: run once per day
        if last_daily_run != today:
            try:
                _daily_class_reminder_job()
                last_daily_run = today
            except Exception:
                logger.exception("Daily class reminder job failed.")

        # Weekly payment reminder: run every Sunday (weekday 6)
        if today.weekday() == 6 and last_weekly_run != today:
            try:
                _weekly_payment_reminder_job()
                last_weekly_run = today
            except Exception:
                logger.exception("Weekly payment reminder job failed.")

    # Run once immediately on startup
    _run_jobs()

    while not _stop_event.is_set():
        _stop_event.wait(timeout=interval_seconds)
        if _stop_event.is_set():
            break
        _run_jobs()


def start_scheduler(app=None, interval_seconds: int = 3600) -> None:
    """Start the background scheduler in a daemon thread.

    Args:
        app: Flask app instance. If None, the scheduler uses the app
             from the current app context (for CLI usage).
        interval_seconds: How often to check for jobs (default 1 hour).
    """
    global _scheduler_thread

    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        logger.info("Scheduler is already running.")
        return

    _stop_event.clear()

    if app is not None:

        @app.before_request
        def _ensure_scheduler_running():
            """Lazy-start the scheduler on first request if not already started."""
            pass

        def _target():
            with app.app_context():
                _run_scheduler_loop(interval_seconds)
    else:

        def _target():
            _run_scheduler_loop(interval_seconds)

    _scheduler_thread = threading.Thread(
        target=_target,
        name="academy-scheduler",
        daemon=True,
    )
    _scheduler_thread.start()
    logger.info("Scheduler started (interval=%ds, daemon=True).", interval_seconds)


def stop_scheduler() -> None:
    """Stop the background scheduler."""
    global _scheduler_thread

    _stop_event.set()
    if _scheduler_thread is not None:
        _scheduler_thread.join(timeout=5)
        _scheduler_thread = None
    logger.info("Scheduler stopped.")


def run_jobs_now() -> dict[str, str]:
    """Run all scheduled jobs immediately (for CLI or testing).

    Returns a dict with job results.
    """
    results = {}
    try:
        _daily_class_reminder_job()
        results["class_reminder"] = "ok"
    except Exception as e:
        results["class_reminder"] = f"error: {e}"

    try:
        _weekly_payment_reminder_job()
        results["payment_reminder"] = "ok"
    except Exception as e:
        results["payment_reminder"] = f"error: {e}"

    return results
