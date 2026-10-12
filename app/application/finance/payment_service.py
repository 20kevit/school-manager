"""Online payment service — handles ZarinPal integration for student payments.

This module provides two core operations:
1. Initiating an online payment (creates a PENDING transaction, returns redirect URL).
2. Processing the payment callback (verifies with ZarinPal, updates transaction status).

The financial ledger remains the source of truth. PENDING transactions do not affect
the student balance until they become ACTIVE (verified payment).
"""

from __future__ import annotations

import logging
from decimal import Decimal

from flask import current_app

from app.extensions import db
from app.infrastructure.database.models import FinancialTransactionModel, UserModel
from app.infrastructure.payment.gateway import PaymentGateway
from app.infrastructure.payment.null_gateway import NullPaymentGateway

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    """Raised when an online payment operation fails."""


def _get_gateway() -> PaymentGateway:
    """Resolve the payment gateway from app config."""
    merchant_id = current_app.config.get("ZARINPAL_MERCHANT_ID", "")
    sandbox = current_app.config.get("ZARINPAL_SANDBOX", True)

    if not merchant_id:
        return NullPaymentGateway()

    from app.infrastructure.payment.zarinpal import ZarinPalGateway

    return ZarinPalGateway(merchant_id=merchant_id, sandbox=sandbox)


def initiate_online_payment(
    student_user_id: int,
    amount: Decimal,
    description: str,
    callback_url: str,
) -> dict:
    """Initiate an online payment via ZarinPal.

    Creates a PENDING FinancialTransaction (does not affect balance),
    then calls ZarinPal to get an authority code and redirect URL.

    Args:
        student_user_id: The student's user ID.
        amount: Payment amount in Toman.
        description: Payment description.
        callback_url: URL for ZarinPal to redirect after payment.

    Returns:
        dict with 'transaction_id' and 'payment_url'.

    Raises:
        PaymentError: If validation fails or gateway rejects the request.
    """
    if amount <= 0:
        raise PaymentError("مبلغ پرداخت باید مثبت باشد.")

    student = UserModel.query.get(student_user_id)
    if student is None:
        raise PaymentError("دانش‌آموز یافت نشد.")
    if not student.has_role("STUDENT"):
        raise PaymentError("کاربر دانش‌آموز نیست.")

    gateway = _get_gateway()
    result = gateway.create_payment(
        amount=amount,
        description=description,
        callback_url=callback_url,
    )

    if not result.success:
        raise PaymentError(f"خطا در اتصال به درگاه پرداخت: {result.error}")

    # Create a PENDING transaction — does not affect balance
    transaction = FinancialTransactionModel(
        student_user_id=student_user_id,
        amount=amount,
        transaction_type="PAYMENT",
        category="OTHER",
        description=description or "پرداخت آنلاین",
        reference_number=result.authority,
        payment_method="ONLINE",
        status="PENDING",
    )
    db.session.add(transaction)
    db.session.commit()

    logger.info(
        "Online payment initiated: transaction_id=%d, authority=%s, amount=%s",
        transaction.id,
        result.authority,
        amount,
    )

    return {
        "transaction_id": transaction.id,
        "payment_url": result.payment_url,
    }


def process_payment_callback(
    authority: str,
    amount: Decimal,
    callback_status: str,
) -> dict:
    """Process the ZarinPal payment callback.

    Called when ZarinPal redirects the user back after payment.
    Verifies the payment with ZarinPal and updates the transaction status.

    The lookup authority (reference_number) is immutable: verification
    results are stored in gateway_ref_id and the authority is preserved,
    so duplicate callbacks stay correlatable and idempotent.

    Args:
        authority: The authority code from the callback query.
        amount: The payment amount (must match the original).
        callback_status: The 'Status' query parameter from ZarinPal.

    Returns:
        dict with 'success', 'transaction_id', 'ref_id', 'message'.
    """
    # Find the transaction by authority code (any status: PENDING for first
    # delivery, ACTIVE/FAILED for duplicate or retried deliveries).
    transaction = FinancialTransactionModel.query.filter_by(
        reference_number=authority,
        payment_method="ONLINE",
    ).first()

    if transaction is None:
        logger.warning("Payment callback for unknown authority: %s", authority)
        return {
            "success": False,
            "transaction_id": None,
            "ref_id": "",
            "message": "تراکنش یافت نشد.",
        }

    if Decimal(str(amount)) != Decimal(str(transaction.amount)):
        logger.warning(
            "Payment callback amount mismatch: transaction_id=%d", transaction.id
        )
        return {
            "success": False,
            "transaction_id": transaction.id,
            "ref_id": transaction.gateway_ref_id or "",
            "message": "مبلغ پرداخت مطابقت ندارد.",
        }

    # Duplicate delivery of an already-verified payment: idempotent success.
    # No state changes, no new ledger rows, no duplicate notifications.
    if transaction.status == "ACTIVE":
        return {
            "success": True,
            "transaction_id": transaction.id,
            "ref_id": transaction.gateway_ref_id or "",
            "message": "پرداخت قبلاً ثبت شده است.",
        }

    # If ZarinPal reported user cancellation
    if callback_status != "OK":
        transaction.status = "FAILED"
        db.session.commit()
        logger.info(
            "Payment cancelled by user: transaction_id=%d, authority=%s",
            transaction.id,
            authority,
        )
        return {
            "success": False,
            "transaction_id": transaction.id,
            "ref_id": "",
            "message": "پرداخت لغو شد.",
        }

    # Verify with ZarinPal (also for previously FAILED rows: a transient
    # failure must not permanently block a completed payment, and the
    # provider remains the ground truth).
    gateway = _get_gateway()
    result = gateway.verify_payment(
        authority=authority,
        amount=transaction.amount,
    )

    if result.success:
        transaction.status = "ACTIVE"
        transaction.gateway_ref_id = result.ref_id or transaction.gateway_ref_id
        db.session.commit()
        logger.info(
            "Payment verified: transaction_id=%d, ref_id=%s",
            transaction.id,
            result.ref_id,
        )

        # Trigger in-app notification to the student
        _notify_payment_success(transaction)

        return {
            "success": True,
            "transaction_id": transaction.id,
            "ref_id": result.ref_id,
            "message": "پرداخت با موفقیت انجام شد.",
        }
    else:
        transaction.status = "FAILED"
        db.session.commit()
        logger.warning(
            "Payment verification failed: transaction_id=%d, authority=%s, error=%s",
            transaction.id,
            authority,
            result.error,
        )
        return {
            "success": False,
            "transaction_id": transaction.id,
            "ref_id": "",
            "message": f"پرداخت تأیید نشد: {result.error}",
        }


def _notify_payment_success(transaction: FinancialTransactionModel) -> None:
    """Send an in-app notification when a payment is successfully verified.

    Uses the notification service to create and send a notification.
    Gracefully degrades if the notification system is unavailable.
    """
    try:
        from app.application.notification import notification_service
        from app.domain.notification import NotificationType

        ref_id = transaction.gateway_ref_id or transaction.reference_number or "-"
        amount_str = f"{transaction.amount:,.0f}"

        notification_service.create_in_app_notification(
            user_id=transaction.student_user_id,
            title="تاییدیه پرداخت",
            message=(
                f"پرداخت شما به مبلغ {amount_str} تومان با کد پیگیری {ref_id} "
                f"با موفقیت ثبت شد."
            ),
            notification_type=NotificationType.PAYMENT_RECEIVED,
            link="/finance/receipt/" + str(transaction.id),
        )
    except Exception:
        logger.exception(
            "Failed to send payment notification for transaction_id=%d",
            transaction.id,
        )
