"""Payment gateway abstraction layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PaymentRequestResult:
    """Result from a payment request (initiating a payment)."""

    success: bool
    authority: str = ""
    payment_url: str = ""
    error: str = ""
    error_code: int = 0


@dataclass
class PaymentVerificationResult:
    """Result from a payment verification (confirming a payment)."""

    success: bool
    ref_id: str = ""
    error: str = ""
    error_code: int = 0
    card_pan: str = ""


class PaymentGateway(ABC):
    """Abstract base class for payment gateway providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique gateway name (e.g. 'zarinpal')."""

    @abstractmethod
    def create_payment(
        self,
        amount: Decimal,
        description: str,
        callback_url: str,
    ) -> PaymentRequestResult:
        """Initiate a payment request and return authority code + redirect URL."""

    @abstractmethod
    def verify_payment(
        self,
        authority: str,
        amount: Decimal,
    ) -> PaymentVerificationResult:
        """Verify a payment after the user completes (or fails) the gateway redirect."""
