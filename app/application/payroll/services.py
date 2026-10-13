"""Payroll calculation and teacher payment management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

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
    note: str = ""


@dataclass
class PayrollSummary:
    """Summary of calculated payroll for a teacher over a period."""

    teacher_user_id: int
    period_start: date
    period_end: date
    total_sessions: int = 0
    gross_amount: Decimal = Decimal("0")
    breakdown_per_class: list[ClassBreakdown] = field(default_factory=list)
    # ACTIVE PAYMENTs in the period with no class attribution. Excluded from
    # every class breakdown by construction; surfaced here so unattributed
    # money stays visible instead of silently vanishing from payroll.
    unattributed_revenue: Decimal = Decimal("0")


def _get_net_collected_tuition(
    class_id: int, start_date: date, end_date: date
) -> Decimal:
    """Sum net collected tuition for a class in a date range.

    This is gross PAYMENT amount minus REFUND and REVERSAL amounts
    related to payments for the same class, within the same date range.
    This provides a net collected revenue figure for accurate payroll
    calculations when the PERCENTAGE_OF_REVENUE model is used.

    Policy decision: Percentage-based payroll uses NET collected revenue
    (payments minus refunds/reversals) to avoid overpaying on reversed
    or refunded transactions.
    """
    from datetime import datetime, timedelta

    from sqlalchemy.orm import aliased

    start_datetime = datetime(start_date.year, start_date.month, start_date.day)
    end_datetime = datetime(end_date.year, end_date.month, end_date.day) + timedelta(
        days=1
    )

    # Gross payments
    gross = (
        db.session.query(func.coalesce(func.sum(FinancialTransactionModel.amount), 0))
        .filter(
            FinancialTransactionModel.class_id == class_id,
            FinancialTransactionModel.transaction_type == "PAYMENT",
            FinancialTransactionModel.status == "ACTIVE",
            FinancialTransactionModel.created_at >= start_datetime,
            FinancialTransactionModel.created_at < end_datetime,
        )
        .scalar()
    )

    # Alias for the original payment table (left side of join)
    original_payment = aliased(FinancialTransactionModel)

    # Refunds linked to payments in this class (via related_transaction_id)
    refunds = (
        db.session.query(func.coalesce(func.sum(FinancialTransactionModel.amount), 0))
        .select_from(FinancialTransactionModel)
        .join(
            original_payment,
            FinancialTransactionModel.related_transaction_id == original_payment.id,
        )
        .filter(
            FinancialTransactionModel.class_id == class_id,
            FinancialTransactionModel.transaction_type == "REFUND",
            FinancialTransactionModel.status == "ACTIVE",
            FinancialTransactionModel.created_at >= start_datetime,
            FinancialTransactionModel.created_at < end_datetime,
        )
        .scalar()
    )

    # Reversals of payments in this class
    reversals = (
        db.session.query(func.coalesce(func.sum(FinancialTransactionModel.amount), 0))
        .select_from(FinancialTransactionModel)
        .join(
            original_payment,
            FinancialTransactionModel.related_transaction_id == original_payment.id,
        )
        .filter(
            FinancialTransactionModel.class_id == class_id,
            FinancialTransactionModel.transaction_type == "REVERSAL",
            FinancialTransactionModel.status == "ACTIVE",
            FinancialTransactionModel.created_at >= start_datetime,
            FinancialTransactionModel.created_at < end_datetime,
        )
        .scalar()
    )

    gross_val = Decimal(str(gross or 0))
    refunds_val = Decimal(str(refunds or 0))
    reversals_val = Decimal(str(reversals or 0))
    # REVERSAL amounts are already signed (negative for payment reversals),
    # so we ADD them (they're already negative for payment reversals).
    # REFUND amounts are stored positive, so we subtract them.
    return gross_val - refunds_val + reversals_val


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
            # Net collected revenue (gross payments minus linked refunds /
            # reversals). A non-positive net never produces a negative
            # salary: the class amount floors at zero with an explicit note,
            # while collected_revenue keeps the true (possibly negative)
            # figure for auditability.
            collected = _get_net_collected_tuition(class_id, start_date, end_date)
            breakdown.collected_revenue = collected
            if collected <= 0:
                breakdown.amount = Decimal("0")
                breakdown.note = (
                    "Net collected revenue is not positive; "
                    "revenue share floored at zero."
                )
            else:
                breakdown.amount = (collected * contract.rate) / Decimal("100")

        total_gross += breakdown.amount
        summary.breakdown_per_class.append(breakdown)

    summary.gross_amount = total_gross
    summary.unattributed_revenue = _get_unattributed_payments(start_date, end_date)
    return summary


def _get_unattributed_payments(start_date: date, end_date: date) -> Decimal:
    """Sum ACTIVE PAYMENTs in the period with no class attribution.

    These payments are preserved in financial reporting but excluded from
    every class-based payroll calculation until they can be reliably
    attributed to a class. Surfacing the total here keeps them visible.
    """
    from datetime import datetime, timedelta

    start_datetime = datetime(start_date.year, start_date.month, start_date.day)
    end_datetime = datetime(end_date.year, end_date.month, end_date.day) + timedelta(
        days=1
    )

    result = (
        db.session.query(func.coalesce(func.sum(FinancialTransactionModel.amount), 0))
        .filter(
            FinancialTransactionModel.class_id.is_(None),
            FinancialTransactionModel.transaction_type == "PAYMENT",
            FinancialTransactionModel.status == "ACTIVE",
            FinancialTransactionModel.created_at >= start_datetime,
            FinancialTransactionModel.created_at < end_datetime,
        )
        .scalar()
    )
    return Decimal(str(result))


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

    Deductions must stay within [0, gross], so net pay can never go
    negative. Advances or debts need an explicit auditable workflow and
    are rejected here.
    """
    from app.application.finance._locks import pg_advisory_xact_lock

    # Serialize concurrent finalizations for the same teacher+period on
    # PostgreSQL; the unique constraint remains as the backstop.
    pg_advisory_xact_lock(
        db.session, f"payroll:{teacher_user_id}:{period_start}:{period_end}"
    )

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
    if deductions > summary.gross_amount:
        raise PayrollError("کسورات نمی‌تواند از مبلغ ناخالص بیشتر باشد.")

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
    try:
        db.session.commit()
    except IntegrityError:
        # Concurrent finalization won the race after our pre-check read.
        db.session.rollback()
        raise PayrollError("قرارداد پرداخت برای این دوره قبلاً ایجاد شده است.")
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
