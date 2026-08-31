"""Payroll calculation and teacher payment management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import func

from app.extensions import db
from app.infrastructure.database.models import (
    AcademyClassModel,
    EnrollmentModel,
    FinancialTransactionModel,
    SessionModel,
    TeacherContractModel,
    TeacherPaymentModel,
    UserModel,
)


class PayrollError(Exception):
    """Raised when a payroll operation fails."""


# ---------------------------------------------------------------------------
# Contract CRUD
# ---------------------------------------------------------------------------


def create_contract(
    teacher_user_id: int,
    class_id: int | None,
    payment_type: str,
    rate: Decimal,
    start_date: date | None = None,
    end_date: date | None = None,
) -> TeacherContractModel:
    """Create a new teacher contract."""
    if rate <= 0:
        raise PayrollError("نرخ پرداخت باید مثبت باشد.")

    if payment_type not in ("PER_SESSION", "PERCENTAGE_OF_REVENUE"):
        raise PayrollError("نوع پرداخت نامعتبر است.")

    if payment_type == "PERCENTAGE_OF_REVENUE" and (rate <= 0 or rate > 100):
        raise PayrollError("درصد درآمد باید بین ۰ تا ۱۰۰ باشد.")

    teacher = UserModel.query.get(teacher_user_id)
    if teacher is None:
        raise PayrollError("معلم یافت نشد.")

    if class_id is not None:
        academy_class = AcademyClassModel.query.get(class_id)
        if academy_class is None:
            raise PayrollError("کلاس یافت نشد.")

    if end_date is not None and start_date is not None and end_date < start_date:
        raise PayrollError("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد.")

    contract = TeacherContractModel(
        teacher_user_id=teacher_user_id,
        class_id=class_id,
        payment_type=payment_type,
        rate=rate,
        is_active=True,
        start_date=start_date,
        end_date=end_date,
    )
    db.session.add(contract)
    db.session.commit()
    return contract


def update_contract(
    contract: TeacherContractModel,
    *,
    class_id: int | None = None,
    payment_type: str | None = None,
    rate: Decimal | None = None,
    is_active: bool | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> TeacherContractModel:
    """Update an existing teacher contract."""
    if payment_type is not None and payment_type not in (
        "PER_SESSION",
        "PERCENTAGE_OF_REVENUE",
    ):
        raise PayrollError("نوع پرداخت نامعتبر است.")

    effective_type = payment_type or contract.payment_type
    effective_rate = rate if rate is not None else contract.rate

    if effective_rate <= 0:
        raise PayrollError("نرخ پرداخت باید مثبت باشد.")

    if effective_type == "PERCENTAGE_OF_REVENUE" and (
        effective_rate <= 0 or effective_rate > 100
    ):
        raise PayrollError("درصد درآمد باید بین ۰ تا ۱۰۰ باشد.")

    if class_id is not None:
        academy_class = AcademyClassModel.query.get(class_id)
        if academy_class is None:
            raise PayrollError("کلاس یافت نشد.")

    if end_date is not None and start_date is not None and end_date < start_date:
        raise PayrollError("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد.")

    if class_id is not None:
        contract.class_id = class_id
    if payment_type is not None:
        contract.payment_type = payment_type
    if rate is not None:
        contract.rate = rate
    if is_active is not None:
        contract.is_active = is_active
    if start_date is not None:
        contract.start_date = start_date
    if end_date is not None:
        contract.end_date = end_date

    db.session.commit()
    return contract


def delete_contract(contract: TeacherContractModel) -> None:
    """Soft-delete a teacher contract by deactivating it."""
    contract.is_active = False
    db.session.commit()


def list_contracts(
    teacher_user_id: int | None = None,
    active_only: bool = True,
) -> list[TeacherContractModel]:
    """List teacher contracts, optionally filtered by teacher."""
    query = TeacherContractModel.query
    if active_only:
        query = query.filter_by(is_active=True)
    if teacher_user_id is not None:
        query = query.filter_by(teacher_user_id=teacher_user_id)
    return query.order_by(TeacherContractModel.id.desc()).all()


def get_contract(contract_id: int) -> TeacherContractModel | None:
    """Get a contract by ID."""
    return TeacherContractModel.query.get(contract_id)


# ---------------------------------------------------------------------------
# Payroll Calculation
# ---------------------------------------------------------------------------


@dataclass
class ClassBreakdown:
    """Breakdown of earnings for a single class."""

    class_id: int
    class_title: str
    payment_type: str
    rate: Decimal
    session_count: int = 0
    collected_revenue: Decimal = Decimal("0")
    amount: Decimal = Decimal("0")


@dataclass
class PayrollSummary:
    """Summary of calculated payroll for a teacher over a period."""

    teacher_user_id: int
    period_start: date
    period_end: date
    total_sessions: int = 0
    gross_amount: Decimal = Decimal("0")
    breakdown_per_class: list[ClassBreakdown] = field(default_factory=list)


def _get_collected_tuition(class_id: int, start_date: date, end_date: date) -> Decimal:
    """Sum collected tuition (PAYMENT transactions) for a class in a date range.

    Collected tuition = sum of PAYMENT transactions with category=TUITION
    for enrollments in the given class, filtered by transaction creation date.
    """
    from datetime import datetime, timedelta

    start_datetime = datetime(start_date.year, start_date.month, start_date.day)
    end_datetime = datetime(end_date.year, end_date.month, end_date.day) + timedelta(
        days=1
    )

    result = (
        db.session.query(func.coalesce(func.sum(FinancialTransactionModel.amount), 0))
        .filter(
            FinancialTransactionModel.class_id == class_id,
            FinancialTransactionModel.transaction_type == "PAYMENT",
            FinancialTransactionModel.category == "TUITION",
            FinancialTransactionModel.status == "ACTIVE",
            FinancialTransactionModel.created_at >= start_datetime,
            FinancialTransactionModel.created_at < end_datetime,
        )
        .scalar()
    )
    return Decimal(str(result))


def _get_enrollment_count(class_id: int) -> int:
    """Count approved enrollments for a class."""
    return EnrollmentModel.query.filter_by(class_id=class_id, status="APPROVED").count()


def calculate_teacher_payroll(
    teacher_user_id: int,
    start_date: date,
    end_date: date,
) -> PayrollSummary:
    """Calculate payroll for a teacher over a date range.

    Logic:
    1. Fetch all COMPLETED sessions for the teacher's classes in the period.
    2. For each session, find the active contract.
    3. For PER_SESSION: count sessions × rate.
    4. For PERCENTAGE_OF_REVENUE: use collected tuition × percentage.
    """
    summary = PayrollSummary(
        teacher_user_id=teacher_user_id,
        period_start=start_date,
        period_end=end_date,
    )

    completed_sessions = (
        SessionModel.query.join(AcademyClassModel)
        .filter(
            AcademyClassModel.teacher_user_id == teacher_user_id,
            SessionModel.status == "COMPLETED",
            SessionModel.scheduled_date >= start_date,
            SessionModel.scheduled_date <= end_date,
        )
        .all()
    )

    if not completed_sessions:
        return summary

    summary.total_sessions = len(completed_sessions)

    # Group sessions by class
    sessions_by_class: dict[int, list[SessionModel]] = {}
    for session in completed_sessions:
        sessions_by_class.setdefault(session.class_id, []).append(session)

    total_gross = Decimal("0")

    for class_id, sessions in sessions_by_class.items():
        contract = _find_active_contract(teacher_user_id, class_id, start_date)
        if contract is None:
            continue

        academy_class = AcademyClassModel.query.get(class_id)
        class_title = academy_class.title if academy_class else f"کلاس {class_id}"

        breakdown = ClassBreakdown(
            class_id=class_id,
            class_title=class_title,
            payment_type=contract.payment_type,
            rate=contract.rate,
            session_count=len(sessions),
        )

        if contract.payment_type == "PER_SESSION":
            breakdown.amount = Decimal(str(len(sessions))) * contract.rate
        elif contract.payment_type == "PERCENTAGE_OF_REVENUE":
            collected = _get_collected_tuition(class_id, start_date, end_date)
            breakdown.collected_revenue = collected
            breakdown.amount = (collected * contract.rate) / Decimal("100")

        total_gross += breakdown.amount
        summary.breakdown_per_class.append(breakdown)

    summary.gross_amount = total_gross
    return summary


def _find_active_contract(
    teacher_user_id: int,
    class_id: int,
    on_date: date,
) -> TeacherContractModel | None:
    """Find the active contract for a teacher on a specific class and date.

    Priority: class-specific contract > generic contract (class_id=None).
    """
    # Try class-specific first
    contract = (
        TeacherContractModel.query.filter_by(
            teacher_user_id=teacher_user_id,
            class_id=class_id,
            is_active=True,
        )
        .filter(
            (TeacherContractModel.start_date.is_(None))
            | (TeacherContractModel.start_date <= on_date)
        )
        .filter(
            (TeacherContractModel.end_date.is_(None))
            | (TeacherContractModel.end_date >= on_date)
        )
        .first()
    )
    if contract is not None:
        return contract

    # Fallback to generic (all classes) contract
    return (
        TeacherContractModel.query.filter_by(
            teacher_user_id=teacher_user_id,
            class_id=None,
            is_active=True,
        )
        .filter(
            (TeacherContractModel.start_date.is_(None))
            | (TeacherContractModel.start_date <= on_date)
        )
        .filter(
            (TeacherContractModel.end_date.is_(None))
            | (TeacherContractModel.end_date >= on_date)
        )
        .first()
    )


# ---------------------------------------------------------------------------
# Payroll Finalization
# ---------------------------------------------------------------------------


def finalize_payroll(
    teacher_user_id: int,
    period_start: date,
    period_end: date,
    deductions: Decimal = Decimal("0"),
) -> TeacherPaymentModel:
    """Calculate and finalize a payroll record for a teacher.

    Creates a TeacherPayment with status=PENDING.
    Raises PayrollError if no sessions found or payment already exists.
    """
    # Check for existing payment in this period
    existing = TeacherPaymentModel.query.filter_by(
        teacher_user_id=teacher_user_id,
        period_start=period_start,
        period_end=period_end,
    ).first()
    if existing is not None:
        raise PayrollError("قرارداد پرداخت برای این دوره قبلاً ایجاد شده است.")

    summary = calculate_teacher_payroll(teacher_user_id, period_start, period_end)
    if summary.total_sessions == 0:
        raise PayrollError("جلسه تکمیل شده‌ای برای این دوره یافت نشد.")

    if deductions < 0:
        raise PayrollError("کسورات نمی‌تواند منفی باشد.")

    payment = TeacherPaymentModel(
        teacher_user_id=teacher_user_id,
        period_start=period_start,
        period_end=period_end,
        gross_amount=summary.gross_amount,
        deductions=deductions,
        net_amount=summary.gross_amount - deductions,
        status="PENDING",
    )
    db.session.add(payment)
    db.session.commit()
    return payment


def mark_payment_paid(
    payment: TeacherPaymentModel,
) -> TeacherPaymentModel:
    """Mark a teacher payment as paid."""
    if payment.status == "PAID":
        raise PayrollError("این پرداخت قبلاً پرداخت شده است.")

    from datetime import datetime

    payment.status = "PAID"
    payment.paid_at = datetime.now()
    db.session.commit()
    return payment


def list_payments(
    teacher_user_id: int | None = None,
    status: str | None = None,
) -> list[TeacherPaymentModel]:
    """List teacher payment records."""
    query = TeacherPaymentModel.query
    if teacher_user_id is not None:
        query = query.filter_by(teacher_user_id=teacher_user_id)
    if status is not None:
        query = query.filter_by(status=status)
    return query.order_by(TeacherPaymentModel.period_start.desc()).all()


def get_payment(payment_id: int) -> TeacherPaymentModel | None:
    """Get a payment by ID."""
    return TeacherPaymentModel.query.get(payment_id)


def list_teachers_with_payroll_summary(
    period_start: date, period_end: date
) -> list[dict]:
    """List all teachers with their calculated payroll for a period.

    Returns a list of dicts: {teacher, summary, existing_payment}
    """
    teachers = UserModel.query.filter(UserModel.roles.any(name="TEACHER")).all()

    results = []
    for teacher in teachers:
        summary = calculate_teacher_payroll(teacher.id, period_start, period_end)
        existing_payment = TeacherPaymentModel.query.filter_by(
            teacher_user_id=teacher.id,
            period_start=period_start,
            period_end=period_end,
        ).first()
        results.append(
            {
                "teacher": teacher,
                "summary": summary,
                "existing_payment": existing_payment,
            }
        )
    return results
