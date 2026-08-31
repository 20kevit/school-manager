"""Null payment gateway — fallback when no real gateway is configured."""

from __future__ import annotations

from decimal import Decimal

from app.infrastructure.payment.gateway import (
    PaymentGateway,
    PaymentRequestResult,
    PaymentVerificationResult,
)


class NullPaymentGateway(PaymentGateway):
    """Fallback gateway that rejects all operations."""

    @property
    def name(self) -> str:
        return "null"

    def create_payment(
        self,
        amount: Decimal,
        description: str,
        callback_url: str,
    ) -> PaymentRequestResult:
        return PaymentRequestResult(
            success=False,
            error="No payment gateway configured.",
        )

    def verify_payment(
        self,
        authority: str,
        amount: Decimal,
    ) -> PaymentVerificationResult:
        return PaymentVerificationResult(
            success=False,
            error="No payment gateway configured.",
        )
