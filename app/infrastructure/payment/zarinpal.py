"""ZarinPal payment gateway adapter.

Implements the PaymentGateway interface for ZarinPal's REST API (v4).
Supports both sandbox and production modes.

Sandbox endpoints:
    Payment Request:  https://sandbox.zarinpal.com/pg/v4/payment/request.json
    Payment Verify:   https://sandbox.zarinpal.com/pg/v4/payment/verify.json
    Gateway Redirect: https://sandbox.zarinpal.com/pg/StartPay/{authority}

Production endpoints:
    Payment Request:  https://payment.zarinpal.com/pg/v4/payment/request.json
    Payment Verify:   https://payment.zarinpal.com/pg/v4/payment/verify.json
    Gateway Redirect: https://www.zarinpal.com/pg/StartPay/{authority}
"""

from __future__ import annotations

import logging
from decimal import Decimal

import requests

from app.infrastructure.payment.gateway import (
    PaymentGateway,
    PaymentRequestResult,
    PaymentVerificationResult,
)

logger = logging.getLogger(__name__)

# ZarinPal API endpoints
_SANDBOX_BASE = "https://sandbox.zarinpal.com"
_PRODUCTION_BASE = "https://payment.zarinpal.com"
_SANDBOX_GATEWAY_BASE = "https://sandbox.zarinpal.com/pg/StartPay/"
_PRODUCTION_GATEWAY_BASE = "https://www.zarinpal.com/pg/StartPay/"

# Currency: IRT = Toman (what our system uses)
_CURRENCY = "IRT"


class ZarinPalGateway(PaymentGateway):
    """ZarinPal payment gateway implementation."""

    def __init__(self, merchant_id: str, sandbox: bool = True) -> None:
        self._merchant_id = merchant_id
        self._sandbox = sandbox
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    @property
    def name(self) -> str:
        return "zarinpal"

    @property
    def _request_url(self) -> str:
        base = _SANDBOX_BASE if self._sandbox else _PRODUCTION_BASE
        return f"{base}/pg/v4/payment/request.json"

    @property
    def _verify_url(self) -> str:
        base = _SANDBOX_BASE if self._sandbox else _PRODUCTION_BASE
        return f"{base}/pg/v4/payment/verify.json"

    def _gateway_url(self, authority: str) -> str:
        base = _SANDBOX_GATEWAY_BASE if self._sandbox else _PRODUCTION_GATEWAY_BASE
        return f"{base}{authority}"

    def create_payment(
        self,
        amount: Decimal,
        description: str,
        callback_url: str,
    ) -> PaymentRequestResult:
        """Initiate a payment request to ZarinPal.

        Args:
            amount: Payment amount in Toman.
            description: Payment description shown to user.
            callback_url: URL to redirect after payment completion.

        Returns:
            PaymentRequestResult with authority code and payment URL on success.
        """
        # ZarinPal expects amount as integer (Toman)
        amount_int = int(amount)

        payload = {
            "merchant_id": self._merchant_id,
            "amount": amount_int,
            "callback_url": callback_url,
            "description": description,
        }

        try:
            response = self._session.post(
                self._request_url,
                json=payload,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error("ZarinPal request failed: %s", e)
            return PaymentRequestResult(
                success=False,
                error=f"Connection error: {e}",
                error_code=-1,
            )
        except ValueError:
            logger.error("ZarinPal returned invalid JSON")
            return PaymentRequestResult(
                success=False,
                error="Invalid response from payment gateway.",
                error_code=-2,
            )

        # Parse response
        response_data = data.get("data", {})
        errors = data.get("errors", [])
        code = response_data.get("code", 0)

        if errors:
            error_msg = "; ".join(
                f"{e.get('code', '')}: {e.get('message', '')}" for e in errors
            )
            logger.warning("ZarinPal errors: %s", error_msg)
            return PaymentRequestResult(
                success=False,
                error=error_msg,
                error_code=errors[0].get("code", 0) if errors else 0,
            )

        if code == 100:
            authority = response_data.get("authority", "")
            payment_url = self._gateway_url(authority)
            logger.info(
                "ZarinPal payment created: authority=%s, amount=%s",
                authority,
                amount_int,
            )
            return PaymentRequestResult(
                success=True,
                authority=authority,
                payment_url=payment_url,
            )

        # Non-100 code means failure
        error_msg = _zarinpal_error_message(code)
        logger.warning("ZarinPal payment request failed: code=%d", code)
        return PaymentRequestResult(
            success=False,
            error=error_msg,
            error_code=code,
        )

    def verify_payment(
        self,
        authority: str,
        amount: Decimal,
    ) -> PaymentVerificationResult:
        """Verify a payment with ZarinPal.

        Args:
            authority: The authority code from the payment request.
            amount: The original payment amount in Toman.

        Returns:
            PaymentVerificationResult with ref_id on success.
        """
        amount_int = int(amount)

        payload = {
            "merchant_id": self._merchant_id,
            "authority": authority,
            "amount": amount_int,
        }

        try:
            response = self._session.post(
                self._verify_url,
                json=payload,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error("ZarinPal verification request failed: %s", e)
            return PaymentVerificationResult(
                success=False,
                error=f"Connection error: {e}",
                error_code=-1,
            )
        except ValueError:
            logger.error("ZarinPal returned invalid JSON during verification")
            return PaymentVerificationResult(
                success=False,
                error="Invalid response from payment gateway.",
                error_code=-2,
            )

        response_data = data.get("data", {})
        errors = data.get("errors", [])
        code = response_data.get("code", 0)

        if errors:
            error_msg = "; ".join(
                f"{e.get('code', '')}: {e.get('message', '')}" for e in errors
            )
            logger.warning("ZarinPal verification errors: %s", error_msg)
            return PaymentVerificationResult(
                success=False,
                error=error_msg,
                error_code=errors[0].get("code", 0) if errors else 0,
            )

        # Code 100 = verified, 101 = already verified
        if code in (100, 101):
            ref_id = str(response_data.get("ref_id", ""))
            card_pan = response_data.get("card_pan", "")
            logger.info(
                "ZarinPal payment verified: ref_id=%s, authority=%s",
                ref_id,
                authority,
            )
            return PaymentVerificationResult(
                success=True,
                ref_id=ref_id,
                card_pan=card_pan,
            )

        error_msg = _zarinpal_error_message(code)
        logger.warning("ZarinPal verification failed: code=%d", code)
        return PaymentVerificationResult(
            success=False,
            error=error_msg,
            error_code=code,
        )


def _zarinpal_error_message(code: int) -> str:
    """Map ZarinPal error codes to human-readable Persian messages."""
    messages = {
        -1: "اطلاعات ارسال شده ناقص است.",
        -2: "IP یا مرچنت کد صحیح نیست.",
        -3: "مبلغ پرداخت شده کمتر از حداقل پرداخت است.",
        -4: "سطح تأیید پست الکترونیکی شما پایین‌تر از سطح درخواست شده است.",
        -5: "مبلغ پرداخت شده بیشتر از حد پرداخت است.",
        -11: "درخواست مورد نظر یافت نشد.",
        -12: "مرچنت کد فعال نیست.",
        -13: "شما دسترسی به این سرویس ندارید.",
        -14: "سرویس مورد نظر غیرفعال شده است.",
        -15: "سرویس مورد نظر قابلیت پرداخت در برهه فعلی را ندارد.",
        -16: "سطح تأیید پست الکترونیکی کاربر از سطح درخواست شده بالاتر است.",
        -17: "همه‌ی شرایط موجود برای پرداخت مهیا نیست.",
        -18: "耽误: تاریخ انقضای توکن گذشته است.",
        -19: "مبلغ پرداخت شده با مبلغ تراکنش مطابقت ندارد.",
        -20: "پرداخت با موفقیت انجام شد اما قبلاً تأیید شده است.",
        -21: "پرداخت قبلاً برای این تراکنش انجام شده است.",
        -22: "پرداخت ناموفق بود.",
        -23: "خطای غیرمنتظره‌ای رخ داده است.",
        -24: "اعتبار سنجی (Captcha) ناموفق بود.",
    }
    return messages.get(code, f"خطای ناشناخته (کد: {code}).")
