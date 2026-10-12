from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func

from app.extensions import db
from app.infrastructure.database.models import (
    AcademyClassModel,
    EnrollmentModel,
    FinancialTransactionModel,
    UserModel,
)


class FinanceError(Exception):
    """Raised when a financial operation fails."""


# ---------------------------------------------------------------------------
# Charge creation
# ---------------------------------------------------------------------------


def create_charge(
    student_user_id: int,
    amount: Decimal,
    category: str,
    *,
    description: str = "",
    reference_number: str = "",
    enrollment_id: int | None = None,
    class_id: int | None = None,
    created_by: int | None = None,
) -> FinancialTransactionModel:
    """Create a financial charge (negative impact on balance)."""
    if amount <= 0:
        raise FinanceError("Charge amount must be positive.")

    _validate_student(student_user_id)

    transaction = FinancialTransactionModel(
        student_user_id=student_user_id,
        amount=amount,
        transaction_type="CHARGE",
        category=category,
        description=description,
        reference_number=reference_number,
        enrollment_id=enrollment_id,
        class_id=class_id,
        status="ACTIVE",
        created_by=created_by,
    )
    db.session.add(transaction)
    db.session.commit()
    return transaction


def create_tuition_charge(
    student_user_id: int,
    class_id: int,
    enrollment_id: int,
    *,
    created_by: int | None = None,
) -> FinancialTransactionModel:
    """Create a tuition charge from an approved enrollment.

    Uses the class tuition amount at the time of enrollment (snapshot).
    Prevents duplicate tuition charges for the same enrollment.
    """
    existing = FinancialTransactionModel.query.filter_by(
        enrollment_id=enrollment_id,
        category="TUITION",
        transaction_type="CHARGE",
        status="ACTIVE",
    ).first()
    if existing is not None:
        raise FinanceError("Tuition charge already exists for this enrollment.")

    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        raise FinanceError("Class not found.")

    tuition_amount = Decimal(str(academy_class.tuition))
    if tuition_amount <= 0:
        raise FinanceError("Class has no tuition amount set.")

    return create_charge(
        student_user_id=student_user_id,
        amount=tuition_amount,
        category="TUITION",
        description=f"Tuition for class: {academy_class.title}",
        enrollment_id=enrollment_id,
        class_id=class_id,
        created_by=created_by,
    )


# ---------------------------------------------------------------------------
# Payment recording
# ---------------------------------------------------------------------------


def record_payment(
    student_user_id: int,
    amount: Decimal,
    *,
    payment_method: str = "CASH",
    description: str = "",
    reference_number: str = "",
    enrollment_id: int | None = None,
    class_id: int | None = None,
    created_by: int | None = None,
) -> FinancialTransactionModel:
    """Record a payment from a student."""
    if amount <= 0:
        raise FinanceError("Payment amount must be positive.")

    _validate_student(student_user_id)

    transaction = FinancialTransactionModel(
        student_user_id=student_user_id,
        amount=amount,
        transaction_type="PAYMENT",
        category="OTHER",
        description=description or "Payment received",
        reference_number=reference_number,
        payment_method=payment_method,
        enrollment_id=enrollment_id,
        class_id=class_id,
        status="ACTIVE",
        created_by=created_by,
    )
    db.session.add(transaction)
    db.session.commit()
    return transaction


# ---------------------------------------------------------------------------
# Refund
# ---------------------------------------------------------------------------


def record_refund(
    student_user_id: int,
    amount: Decimal,
    *,
    description: str = "",
    reference_number: str = "",
    related_transaction_id: int | None = None,
    enrollment_id: int | None = None,
    class_id: int | None = None,
    created_by: int | None = None,
) -> FinancialTransactionModel:
    """Record a refund to a student.

    When related_transaction_id is given, the original payment is validated
    (must exist, belong to the same student, be ACTIVE, and be a PAYMENT)
    and the refund is capped at the remaining refundable amount, so the
    same payment cannot be refunded twice. Without a link, a standalone
    goodwill refund is recorded as before.

    If the refund is linked to a payment, the class_id is automatically
    inherited from the original payment for revenue tracking purposes.
    """
    if amount <= 0:
        raise FinanceError("Refund amount must be positive.")

    _validate_student(student_user_id)

    if related_transaction_id is not None:
        _validate_refund_link(student_user_id, amount, related_transaction_id)
        # Inherit class_id from the original payment if not explicitly provided
        if class_id is None:
            original = FinancialTransactionModel.query.get(related_transaction_id)
            if original is not None:
                class_id = original.class_id

    transaction = FinancialTransactionModel(
        student_user_id=student_user_id,
        amount=amount,
        transaction_type="REFUND",
        category="OTHER",
        description=description or "Refund issued",
        reference_number=reference_number,
        related_transaction_id=related_transaction_id,
        enrollment_id=enrollment_id,
        class_id=class_id,
        status="ACTIVE",
        created_by=created_by,
    )
    db.session.add(transaction)
    db.session.commit()
    return transaction


# ---------------------------------------------------------------------------
# Discount
# ---------------------------------------------------------------------------


def apply_discount(
    student_user_id: int,
    amount: Decimal,
    *,
    category: str = "TUITION",
    description: str = "",
    enrollment_id: int | None = None,
    class_id: int | None = None,
    created_by: int | None = None,
) -> FinancialTransactionModel:
    """Apply a discount to a student's account."""
    if amount <= 0:
        raise FinanceError("Discount amount must be positive.")

    _validate_student(student_user_id)

    transaction = FinancialTransactionModel(
        student_user_id=student_user_id,
        amount=amount,
        transaction_type="DISCOUNT",
        category=category,
        description=description or "Discount applied",
        enrollment_id=enrollment_id,
        class_id=class_id,
        status="ACTIVE",
        created_by=created_by,
    )
    db.session.add(transaction)
    db.session.commit()
    return transaction


# ---------------------------------------------------------------------------
# Adjustment
# ---------------------------------------------------------------------------


def create_adjustment(
    student_user_id: int,
    amount: Decimal,
    *,
    category: str = "OTHER",
    description: str = "",
    reference_number: str = "",
    created_by: int | None = None,
) -> FinancialTransactionModel:
    """Create a manual adjustment (positive or negative).

    The sign is preserved: a positive amount credits the account, a
    negative amount debits it. Balance calculations consume the stored
    signed value directly, so stripping the sign here would silently
    turn every debit adjustment into a credit.
    """
    signed_amount = Decimal(str(amount))
    if signed_amount == 0:
        raise FinanceError("Adjustment amount cannot be zero.")

    _validate_student(student_user_id)

    transaction = FinancialTransactionModel(
        student_user_id=student_user_id,
        amount=signed_amount,
        transaction_type="ADJUSTMENT",
        category=category,
        description=description or "Manual adjustment",
        reference_number=reference_number,
        status="ACTIVE",
        created_by=created_by,
    )
    db.session.add(transaction)
    db.session.commit()
    return transaction


# ---------------------------------------------------------------------------
# Transaction correction / reversal
# ---------------------------------------------------------------------------


def correct_transaction(
    transaction_id: int,
    *,
    new_amount: Decimal | None = None,
    new_description: str | None = None,
    new_reference_number: str | None = None,
    corrected_by: int | None = None,
) -> FinancialTransactionModel:
    """Correct a transaction by marking the original as CORRECTED and creating a new entry.

    Preserves the original transaction (marked as CORRECTED, excluded from balance)
    and creates a new corrected transaction with the correct values.
    """
    original = FinancialTransactionModel.query.get(transaction_id)
    if original is None:
        raise FinanceError("Transaction not found.")
    if original.status != "ACTIVE":
        raise FinanceError("Only active transactions can be corrected.")

    # Capture old state for audit logging
    old_values = {
        "amount": float(original.amount),
        "transaction_type": original.transaction_type,
        "category": original.category,
        "description": original.description,
        "reference_number": original.reference_number,
        "status": original.status,
    }

    # Mark original as CORRECTED (excluded from balance)
    original.status = "CORRECTED"

    # Create corrected entry with new values
    corrected_amount = new_amount if new_amount is not None else original.amount
    corrected_desc = (
        new_description if new_description is not None else original.description
    )
    corrected_ref = (
        new_reference_number
        if new_reference_number is not None
        else original.reference_number
    )

    corrected = FinancialTransactionModel(
        student_user_id=original.student_user_id,
        amount=corrected_amount,
        transaction_type=original.transaction_type,
        category=original.category,
        description=corrected_desc,
        reference_number=corrected_ref,
        payment_method=original.payment_method,
        enrollment_id=original.enrollment_id,
        class_id=original.class_id,
        related_transaction_id=original.id,
        status="ACTIVE",
        created_by=corrected_by,
    )
    db.session.add(corrected)
    db.session.commit()

    # Audit log
    if corrected_by is not None:
        new_values = {
            "amount": float(corrected_amount),
            "transaction_type": corrected.transaction_type,
            "category": corrected.category,
            "description": corrected_desc,
            "reference_number": corrected_ref,
            "status": "ACTIVE",
        }
        from app.application.audit.audit_service import log as audit_log

        audit_log(
            user_id=corrected_by,
            action="CORRECT",
            entity_type="FINANCIAL_TRANSACTION",
            entity_id=original.id,
            old_values=old_values,
            new_values=new_values,
        )

    return corrected


def reverse_transaction(
    transaction_id: int,
    *,
    description: str = "",
    reversed_by: int | None = None,
) -> FinancialTransactionModel:
    """Reverse a transaction by creating an opposite entry.

    The original remains ACTIVE for historical preservation.
    The REVERSAL entry undoes its financial impact. Each transaction may be
    reversed at most once: a second reversal would double-count, so it is
    rejected while the original stays ACTIVE for history.
    """
    original = FinancialTransactionModel.query.get(transaction_id)
    if original is None:
        raise FinanceError("Transaction not found.")
    if original.status != "ACTIVE":
        raise FinanceError("Only active transactions can be reversed.")

    existing_reversal = FinancialTransactionModel.query.filter_by(
        related_transaction_id=original.id,
        transaction_type="REVERSAL",
        status="ACTIVE",
    ).first()
    if existing_reversal is not None:
        raise FinanceError("This transaction has already been reversed.")

    # Capture old state for audit logging
    old_values = {
        "amount": float(original.amount),
        "transaction_type": original.transaction_type,
        "category": original.category,
        "description": original.description,
        "status": original.status,
    }

    reversal_amount = _compute_reversal_amount(original)

    reversal = FinancialTransactionModel(
        student_user_id=original.student_user_id,
        amount=reversal_amount,
        transaction_type="REVERSAL",
        category=original.category,
        description=description or f"Reversal of transaction #{original.id}",
        reference_number=original.reference_number,
        enrollment_id=original.enrollment_id,
        class_id=original.class_id,
        related_transaction_id=original.id,
        status="ACTIVE",
        created_by=reversed_by,
    )
    db.session.add(reversal)
    db.session.commit()

    # Audit log
    if reversed_by is not None:
        new_values = {
            "amount": float(reversal_amount),
            "transaction_type": "REVERSAL",
            "category": original.category,
            "description": description or f"Reversal of transaction #{original.id}",
            "status": "ACTIVE",
        }
        from app.application.audit.audit_service import log as audit_log

        audit_log(
            user_id=reversed_by,
            action="REVERSE",
            entity_type="FINANCIAL_TRANSACTION",
            entity_id=original.id,
            old_values=old_values,
            new_values=new_values,
        )

    return reversal


# ---------------------------------------------------------------------------
# Balance queries
# ---------------------------------------------------------------------------


def get_student_balance(student_user_id: int) -> Decimal:
    """Calculate student's current balance from all active transactions.

    Positive = student has credit.
    Negative = student owes money.

    REVERSAL and ADJUSTMENT amounts are stored as signed values
    (positive = credit, negative = debt) and used directly.
    """
    result = (
        db.session.query(
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
                    # REVERSAL and ADJUSTMENT: amount is already signed
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
        )
        .filter(
            FinancialTransactionModel.student_user_id == student_user_id,
            FinancialTransactionModel.status == "ACTIVE",
        )
        .scalar()
    )

    return Decimal(str(result)) if result is not None else Decimal("0")


def get_student_balance_by_class(student_user_id: int, class_id: int) -> Decimal:
    """Calculate student's balance for a specific class."""
    result = (
        db.session.query(
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
        )
        .filter(
            FinancialTransactionModel.student_user_id == student_user_id,
            FinancialTransactionModel.class_id == class_id,
            FinancialTransactionModel.status == "ACTIVE",
        )
        .scalar()
    )

    return Decimal(str(result)) if result is not None else Decimal("0")


def get_student_statement(
    student_user_id: int,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[FinancialTransactionModel]:
    """Get student's transaction history ordered by date."""
    return (
        FinancialTransactionModel.query.filter_by(
            student_user_id=student_user_id,
        )
        .filter(FinancialTransactionModel.status == "ACTIVE")
        .order_by(FinancialTransactionModel.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


# ---------------------------------------------------------------------------
# Enrollment integration
# ---------------------------------------------------------------------------


def on_enrollment_approved(
    enrollment: EnrollmentModel,
) -> FinancialTransactionModel | None:
    """Handle tuition charge creation when enrollment is approved.

    Called from enrollment_service.approve_enrollment().
    Idempotent: returns existing charge if already created.
    """
    existing = FinancialTransactionModel.query.filter_by(
        enrollment_id=enrollment.id,
        category="TUITION",
        transaction_type="CHARGE",
        status="ACTIVE",
    ).first()
    if existing is not None:
        return existing

    academy_class = AcademyClassModel.query.get(enrollment.class_id)
    if academy_class is None:
        return None

    tuition_amount = Decimal(str(academy_class.tuition))
    if tuition_amount <= 0:
        return None

    return create_tuition_charge(
        student_user_id=enrollment.student_user_id,
        class_id=enrollment.class_id,
        enrollment_id=enrollment.id,
    )


def on_enrollment_cancelled(
    enrollment: EnrollmentModel,
) -> FinancialTransactionModel | None:
    """Handle financial reversal when an approved enrollment is cancelled.

    Creates a reversal transaction for any active tuition charge.
    The original charge remains ACTIVE for historical preservation;
    the reversal undoes its financial impact.
    """
    if enrollment.status != "CANCELLED":
        return None

    tuition_charge = FinancialTransactionModel.query.filter_by(
        enrollment_id=enrollment.id,
        category="TUITION",
        transaction_type="CHARGE",
        status="ACTIVE",
    ).first()
    if tuition_charge is None:
        return None

    academy_class = AcademyClassModel.query.get(enrollment.class_id)
    class_title = academy_class.title if academy_class else "Unknown"

    # CHARGE reversal should be positive (adds back to balance)
    reversal_amount = _compute_reversal_amount(tuition_charge)

    reversal = FinancialTransactionModel(
        student_user_id=enrollment.student_user_id,
        amount=reversal_amount,
        transaction_type="REVERSAL",
        category="TUITION",
        description=f"Tuition reversal for cancelled enrollment in class: {class_title}",
        enrollment_id=enrollment.id,
        class_id=enrollment.class_id,
        related_transaction_id=tuition_charge.id,
        status="ACTIVE",
    )
    db.session.add(reversal)
    db.session.commit()
    return reversal


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def get_debt_report() -> list[dict]:
    """Get students with outstanding negative balances (they owe money)."""
    balances = _get_all_student_balances()
    return [
        {"student_user_id": sid, "balance": bal}
        for sid, bal in balances.items()
        if bal < 0
    ]


def get_credit_report() -> list[dict]:
    """Get students with positive balances (they have credit)."""
    balances = _get_all_student_balances()
    return [
        {"student_user_id": sid, "balance": bal}
        for sid, bal in balances.items()
        if bal > 0
    ]


def get_revenue_report(
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """Get revenue summary for a date range."""
    query = FinancialTransactionModel.query.filter(
        FinancialTransactionModel.status == "ACTIVE",
        FinancialTransactionModel.transaction_type.in_(["PAYMENT", "DISCOUNT"]),
    )

    if start_date is not None:
        query = query.filter(
            FinancialTransactionModel.created_at
            >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date is not None:
        query = query.filter(
            FinancialTransactionModel.created_at
            <= datetime.combine(end_date, datetime.max.time())
        )

    payments = (
        query.filter_by(transaction_type="PAYMENT")
        .with_entities(func.coalesce(func.sum(FinancialTransactionModel.amount), 0))
        .scalar()
    )

    discounts = (
        query.filter_by(transaction_type="DISCOUNT")
        .with_entities(func.coalesce(func.sum(FinancialTransactionModel.amount), 0))
        .scalar()
    )

    refunds = FinancialTransactionModel.query.filter(
        FinancialTransactionModel.status == "ACTIVE",
        FinancialTransactionModel.transaction_type == "REFUND",
    )
    if start_date is not None:
        refunds = refunds.filter(
            FinancialTransactionModel.created_at
            >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date is not None:
        refunds = refunds.filter(
            FinancialTransactionModel.created_at
            <= datetime.combine(end_date, datetime.max.time())
        )
    refund_total = refunds.with_entities(
        func.coalesce(func.sum(FinancialTransactionModel.amount), 0)
    ).scalar()

    return {
        "payments": Decimal(str(payments)),
        "discounts": Decimal(str(discounts)),
        "refunds": Decimal(str(refund_total)),
        "net_revenue": Decimal(str(payments)) - Decimal(str(refund_total)),
    }


def get_class_financial_summary(class_id: int) -> dict:
    """Get financial summary for a class."""
    from app.infrastructure.database.models import EnrollmentModel

    enrolled_students = (
        EnrollmentModel.query.filter_by(class_id=class_id, status="APPROVED")
        .with_entities(EnrollmentModel.student_user_id)
        .all()
    )
    student_ids = [s.student_user_id for s in enrolled_students]

    if not student_ids:
        return {
            "enrolled_count": 0,
            "total_tuition": Decimal("0"),
            "total_paid": Decimal("0"),
            "total_discounts": Decimal("0"),
            "total_refunds": Decimal("0"),
            "total_outstanding": Decimal("0"),
            "students": [],
        }

    transactions = FinancialTransactionModel.query.filter(
        FinancialTransactionModel.class_id == class_id,
        FinancialTransactionModel.student_user_id.in_(student_ids),
        FinancialTransactionModel.status == "ACTIVE",
    ).all()

    total_tuition = Decimal("0")
    total_paid = Decimal("0")
    total_discounts = Decimal("0")
    total_refunds = Decimal("0")

    for t in transactions:
        amt = Decimal(str(t.amount))
        if t.transaction_type == "CHARGE":
            total_tuition += amt
        elif t.transaction_type == "PAYMENT":
            total_paid += amt
        elif t.transaction_type == "DISCOUNT":
            total_discounts += amt
        elif t.transaction_type == "REFUND":
            total_refunds += amt

    student_balances = {}
    for t in transactions:
        sid = t.student_user_id
        if sid not in student_balances:
            student_balances[sid] = Decimal("0")
        student_balances[sid] += _signed_amount(t)

    students_data = []
    for sid in student_ids:
        bal = student_balances.get(sid, Decimal("0"))
        students_data.append(
            {
                "student_user_id": sid,
                "balance": bal,
                "status": "PAID"
                if bal >= 0
                else ("PARTIALLY_PAID" if bal > -total_tuition else "UNPAID"),
            }
        )

    return {
        "enrolled_count": len(student_ids),
        "total_tuition": total_tuition,
        "total_paid": total_paid,
        "total_discounts": total_discounts,
        "total_refunds": total_refunds,
        "total_outstanding": abs(
            min(Decimal("0"), sum(s["balance"] for s in students_data))
        ),
        "students": students_data,
    }


def get_transaction_report(
    *,
    student_user_id: int | None = None,
    class_id: int | None = None,
    category: str | None = None,
    transaction_type: str | None = None,
    payment_method: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[FinancialTransactionModel]:
    """Get filtered transaction report."""
    query = FinancialTransactionModel.query.filter(
        FinancialTransactionModel.status == "ACTIVE"
    )

    if student_user_id is not None:
        query = query.filter_by(student_user_id=student_user_id)
    if class_id is not None:
        query = query.filter_by(class_id=class_id)
    if category is not None:
        query = query.filter_by(category=category)
    if transaction_type is not None:
        query = query.filter_by(transaction_type=transaction_type)
    if payment_method is not None:
        query = query.filter_by(payment_method=payment_method)
    if start_date is not None:
        query = query.filter(
            FinancialTransactionModel.created_at
            >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date is not None:
        query = query.filter(
            FinancialTransactionModel.created_at
            <= datetime.combine(end_date, datetime.max.time())
        )

    return (
        query.order_by(FinancialTransactionModel.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_dashboard_summary() -> dict:
    """Get financial dashboard summary for admin."""
    all_balances = _get_all_student_balances()

    total_debt = Decimal("0")
    total_credit = Decimal("0")
    debtors_count = 0
    credit_count = 0

    for bal in all_balances.values():
        if bal < 0:
            total_debt += abs(bal)
            debtors_count += 1
        elif bal > 0:
            total_credit += bal
            credit_count += 1

    today = date.today()
    month_start = today.replace(day=1)

    today_payments = (
        FinancialTransactionModel.query.filter(
            FinancialTransactionModel.status == "ACTIVE",
            FinancialTransactionModel.transaction_type == "PAYMENT",
            func.date(FinancialTransactionModel.created_at) == today,
        )
        .with_entities(func.coalesce(func.sum(FinancialTransactionModel.amount), 0))
        .scalar()
    )

    today_online_payments_count = FinancialTransactionModel.query.filter(
        FinancialTransactionModel.status == "ACTIVE",
        FinancialTransactionModel.transaction_type == "PAYMENT",
        FinancialTransactionModel.payment_method == "ONLINE",
        func.date(FinancialTransactionModel.created_at) == today,
    ).count()

    today_online_payments_amount = (
        FinancialTransactionModel.query.filter(
            FinancialTransactionModel.status == "ACTIVE",
            FinancialTransactionModel.transaction_type == "PAYMENT",
            FinancialTransactionModel.payment_method == "ONLINE",
            func.date(FinancialTransactionModel.created_at) == today,
        )
        .with_entities(func.coalesce(func.sum(FinancialTransactionModel.amount), 0))
        .scalar()
    )

    month_payments = (
        FinancialTransactionModel.query.filter(
            FinancialTransactionModel.status == "ACTIVE",
            FinancialTransactionModel.transaction_type == "PAYMENT",
            FinancialTransactionModel.created_at
            >= datetime.combine(month_start, datetime.min.time()),
        )
        .with_entities(func.coalesce(func.sum(FinancialTransactionModel.amount), 0))
        .scalar()
    )

    total_payments = (
        FinancialTransactionModel.query.filter(
            FinancialTransactionModel.status == "ACTIVE",
            FinancialTransactionModel.transaction_type == "PAYMENT",
        )
        .with_entities(func.coalesce(func.sum(FinancialTransactionModel.amount), 0))
        .scalar()
    )

    total_refunds = (
        FinancialTransactionModel.query.filter(
            FinancialTransactionModel.status == "ACTIVE",
            FinancialTransactionModel.transaction_type == "REFUND",
        )
        .with_entities(func.coalesce(func.sum(FinancialTransactionModel.amount), 0))
        .scalar()
    )

    total_discounts = (
        FinancialTransactionModel.query.filter(
            FinancialTransactionModel.status == "ACTIVE",
            FinancialTransactionModel.transaction_type == "DISCOUNT",
        )
        .with_entities(func.coalesce(func.sum(FinancialTransactionModel.amount), 0))
        .scalar()
    )

    total_tuition = (
        FinancialTransactionModel.query.filter(
            FinancialTransactionModel.status == "ACTIVE",
            FinancialTransactionModel.transaction_type == "CHARGE",
            FinancialTransactionModel.category == "TUITION",
        )
        .with_entities(func.coalesce(func.sum(FinancialTransactionModel.amount), 0))
        .scalar()
    )

    return {
        "total_debt": total_debt,
        "total_credit": total_credit,
        "debtors_count": debtors_count,
        "credit_count": credit_count,
        "total_payments": Decimal(str(total_payments)),
        "today_payments": Decimal(str(today_payments)),
        "today_online_payments_count": today_online_payments_count,
        "today_online_payments_amount": Decimal(str(today_online_payments_amount)),
        "month_payments": Decimal(str(month_payments)),
        "total_refunds": Decimal(str(total_refunds)),
        "total_discounts": Decimal(str(total_discounts)),
        "tuition_revenue": Decimal(str(total_tuition)),
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _compute_reversal_amount(original: FinancialTransactionModel) -> Decimal:
    """Compute the signed amount for a REVERSAL that undoes the original.

    PAYMENT (+amt) → REVERSAL (-amt)
    CHARGE (-amt)  → REVERSAL (+amt)
    DISCOUNT (+amt) → REVERSAL (-amt)
    REFUND (-amt)  → REVERSAL (+amt)
    ADJUSTMENT/REVERSAL (stored signed) → REVERSAL (-stored)
    """
    if original.transaction_type in ("PAYMENT", "DISCOUNT"):
        return -abs(original.amount)
    if original.transaction_type in ("CHARGE", "REFUND"):
        return abs(original.amount)
    # ADJUSTMENT and REVERSAL amounts are stored signed: negate exactly.
    return -Decimal(str(original.amount))


def _signed_amount(tx: FinancialTransactionModel) -> Decimal:
    """Compute signed amount for a transaction model instance."""
    amt = Decimal(str(tx.amount))
    if tx.transaction_type in ("PAYMENT", "DISCOUNT"):
        return amt
    if tx.transaction_type in ("CHARGE", "REFUND"):
        return -amt
    # REVERSAL and ADJUSTMENT: amount is already signed
    return amt


def _validate_student(student_user_id: int) -> None:
    """Validate that the student exists and has STUDENT role."""
    student = UserModel.query.get(student_user_id)
    if student is None:
        raise FinanceError("Student not found.")
    if not student.has_role("STUDENT"):
        raise FinanceError("User is not a student.")


def get_remaining_refundable(payment_id: int) -> Decimal:
    """Remaining refundable amount for a payment (never negative)."""
    original = FinancialTransactionModel.query.get(payment_id)
    if original is None:
        return Decimal("0")
    refunded = (
        db.session.query(func.coalesce(func.sum(FinancialTransactionModel.amount), 0))
        .filter(
            FinancialTransactionModel.related_transaction_id == payment_id,
            FinancialTransactionModel.transaction_type == "REFUND",
            FinancialTransactionModel.status == "ACTIVE",
        )
        .scalar()
    )
    remaining = Decimal(str(original.amount)) - Decimal(str(refunded))
    return remaining if remaining > 0 else Decimal("0")


def _validate_refund_link(
    student_user_id: int, amount: Decimal, related_transaction_id: int
) -> None:
    """Validate a refund against its original payment.

    The original must exist, belong to the same student, be ACTIVE, and be
    a PAYMENT; the refund must not exceed the remaining refundable amount.
    """
    original = FinancialTransactionModel.query.get(related_transaction_id)
    if original is None:
        raise FinanceError("Original transaction not found.")
    if original.student_user_id != student_user_id:
        raise FinanceError("Refund does not belong to the original payment account.")
    if original.status != "ACTIVE":
        raise FinanceError("Only active payments can be refunded.")
    if original.transaction_type != "PAYMENT":
        raise FinanceError("Only payments can be refunded.")
    remaining = get_remaining_refundable(related_transaction_id)
    if Decimal(str(amount)) > remaining:
        raise FinanceError(
            f"Refund exceeds the remaining refundable amount ({remaining})."
        )


def _get_all_student_balances() -> dict[int, Decimal]:
    """Get balances for all students who have transactions."""
    rows = (
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
        .filter(
            FinancialTransactionModel.status == "ACTIVE",
        )
        .group_by(
            FinancialTransactionModel.student_user_id,
        )
        .all()
    )

    return {row[0]: Decimal(str(row[1])) for row in rows}
