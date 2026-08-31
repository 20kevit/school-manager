from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum


class PaymentType(StrEnum):
    """How a teacher is compensated."""

    PER_SESSION = "PER_SESSION"
    PERCENTAGE_OF_REVENUE = "PERCENTAGE_OF_REVENUE"


class PayrollStatus(StrEnum):
    """Status of a teacher payment record."""

    PENDING = "PENDING"
    PAID = "PAID"


class TeacherContract:
    """Teacher contract domain entity.

    Defines payment terms for a teacher, optionally scoped to a specific class.
    """

    def __init__(
        self,
        id: int | None,
        teacher_user_id: int,
        class_id: int | None,
        payment_type: PaymentType,
        rate: Decimal,
        is_active: bool = True,
        start_date: date | None = None,
        end_date: date | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.teacher_user_id = teacher_user_id
        self.class_id = class_id
        self.payment_type = payment_type
        self.rate = rate
        self.is_active = is_active
        self.start_date = start_date
        self.end_date = end_date
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def __repr__(self) -> str:
        return (
            f"<TeacherContract id={self.id} "
            f"teacher={self.teacher_user_id} "
            f"type={self.payment_type} "
            f"rate={self.rate}>"
        )


class TeacherPayment:
    """Teacher payment domain entity.

    Records a finalized payout to a teacher for a specific period.
    """

    def __init__(
        self,
        id: int | None,
        teacher_user_id: int,
        period_start: date,
        period_end: date,
        gross_amount: Decimal,
        deductions: Decimal = Decimal("0"),
        net_amount: Decimal | None = None,
        status: PayrollStatus = PayrollStatus.PENDING,
        paid_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.teacher_user_id = teacher_user_id
        self.period_start = period_start
        self.period_end = period_end
        self.gross_amount = gross_amount
        self.deductions = deductions
        self.net_amount = (
            net_amount if net_amount is not None else gross_amount - deductions
        )
        self.status = status
        self.paid_at = paid_at
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def __repr__(self) -> str:
        return (
            f"<TeacherPayment id={self.id} "
            f"teacher={self.teacher_user_id} "
            f"gross={self.gross_amount} "
            f"status={self.status}>"
        )
