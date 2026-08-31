from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class TransactionType(StrEnum):
    """Direction/type of a financial transaction."""

    CHARGE = "CHARGE"
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"
    DISCOUNT = "DISCOUNT"
    ADJUSTMENT = "ADJUSTMENT"
    REVERSAL = "REVERSAL"


class TransactionCategory(StrEnum):
    """Financial reason/category for a transaction."""

    TUITION = "TUITION"
    BOOK = "BOOK"
    EQUIPMENT = "EQUIPMENT"
    EXAM = "EXAM"
    OTHER = "OTHER"


class PaymentMethod(StrEnum):
    """How a payment was made."""

    CASH = "CASH"
    CARD = "CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    ONLINE = "ONLINE"
    OTHER = "OTHER"


class TransactionStatus(StrEnum):
    """Status of a financial transaction."""

    ACTIVE = "ACTIVE"
    VOIDED = "VOIDED"
    CORRECTED = "CORRECTED"
    PENDING = "PENDING"
    FAILED = "FAILED"


class FinancialTransaction:
    """Financial transaction domain entity.

    Represents any financial event in a student's account.
    The student's balance is derived from all valid (ACTIVE) transactions.

    Sign convention (from student perspective):
    - CHARGE:  negative (student owes)
    - PAYMENT: positive (student paid)
    - REFUND:  negative (money returned to student)
    - DISCOUNT: positive (reduces amount owed)
    - ADJUSTMENT: can be positive or negative
    - REVERSAL: opposite sign of the original transaction
    """

    def __init__(
        self,
        id: int | None,
        student_user_id: int,
        amount: Decimal,
        transaction_type: TransactionType,
        category: TransactionCategory,
        description: str = "",
        reference_number: str = "",
        payment_method: PaymentMethod | None = None,
        enrollment_id: int | None = None,
        class_id: int | None = None,
        related_transaction_id: int | None = None,
        status: TransactionStatus = TransactionStatus.ACTIVE,
        created_by: int | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.student_user_id = student_user_id
        self.amount = amount
        self.transaction_type = transaction_type
        self.category = category
        self.description = description
        self.reference_number = reference_number
        self.payment_method = payment_method
        self.enrollment_id = enrollment_id
        self.class_id = class_id
        self.related_transaction_id = related_transaction_id
        self.status = status
        self.created_by = created_by
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    @property
    def signed_amount(self) -> Decimal:
        """Return amount with sign based on transaction type.

        Positive = student credit (payment, discount).
        Negative = student debt (charge, refund).
        """
        if self.transaction_type in (
            TransactionType.PAYMENT,
            TransactionType.DISCOUNT,
        ):
            return abs(self.amount)
        if self.transaction_type in (
            TransactionType.CHARGE,
            TransactionType.REFUND,
        ):
            return -abs(self.amount)
        # ADJUSTMENT and REVERSAL can be positive or negative
        return self.amount

    def is_active(self) -> bool:
        return self.status == TransactionStatus.ACTIVE

    def void(self) -> None:
        """Mark transaction as voided (soft delete)."""
        if self.status == TransactionStatus.VOIDED:
            raise ValueError("Transaction is already voided.")
        self.status = TransactionStatus.VOIDED

    def __repr__(self) -> str:
        return (
            f"<FinancialTransaction id={self.id} "
            f"student={self.student_user_id} "
            f"type={self.transaction_type} "
            f"amount={self.amount} "
            f"status={self.status}>"
        )
