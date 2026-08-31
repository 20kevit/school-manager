"""Tests for P18 — ZarinPal Integration & Online Payments."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.application.finance import finance_service, payment_service
from app.infrastructure.database.models import (
    FinancialTransactionModel,
    RoleModel,
    StudentProfileModel,
    UserModel,
)
from app.infrastructure.payment.gateway import (
    PaymentRequestResult,
    PaymentVerificationResult,
)
from app.infrastructure.payment.null_gateway import NullPaymentGateway
from app.infrastructure.payment.zarinpal import ZarinPalGateway

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def student(db):
    """Create a student user with profile for payment tests."""
    user = UserModel(login="pay_student")
    user.set_password("pass123")
    role = RoleModel(name="STUDENT")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.flush()

    profile = StudentProfileModel(
        user_id=user.id,
        first_name="Ali",
        last_name="Rezaei",
        national_id="1111111111",
        mobile_phone="09121111111",
        birth_date=date(2000, 1, 15),
        gender="MALE",
    )
    db.session.add(profile)
    db.session.commit()
    return user


@pytest.fixture
def student_with_debt(db, student):
    """Create a student with an outstanding debt (CHARGE)."""
    finance_service.create_charge(
        student_user_id=student.id,
        amount=Decimal("500000"),
        category="TUITION",
        description="Tuition charge",
    )
    return student


@pytest.fixture
def parent_of_student(db, student):
    """Create a parent linked to the student."""
    from app.infrastructure.database.models import ParentProfileModel

    user = UserModel(login="pay_parent")
    user.set_password("pass123")
    role = RoleModel(name="PARENT")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.flush()

    profile = ParentProfileModel(
        user_id=user.id,
        first_name="Reza",
        last_name="Rezaei",
        national_id="2222222222",
        mobile_phone="09122222222",
    )
    db.session.add(profile)
    db.session.flush()

    student_profile = StudentProfileModel.query.filter_by(user_id=student.id).first()
    if student_profile:
        profile.children.append(student_profile)

    db.session.commit()
    return user


# ---------------------------------------------------------------------------
# ZarinPal Gateway Tests
# ---------------------------------------------------------------------------


class TestZarinPalGateway:
    """Tests for the ZarinPal gateway adapter."""

    def test_name(self):
        gw = ZarinPalGateway(merchant_id="test-merchant", sandbox=True)
        assert gw.name == "zarinpal"

    def test_sandbox_urls(self):
        gw = ZarinPalGateway(merchant_id="test-merchant", sandbox=True)
        assert "sandbox.zarinpal.com" in gw._request_url
        assert "sandbox.zarinpal.com" in gw._verify_url
        assert "sandbox.zarinpal.com/pg/StartPay/" in gw._gateway_url("test-auth")

    def test_production_urls(self):
        gw = ZarinPalGateway(merchant_id="test-merchant", sandbox=False)
        assert "payment.zarinpal.com" in gw._request_url
        assert "payment.zarinpal.com" in gw._verify_url
        assert "www.zarinpal.com/pg/StartPay/" in gw._gateway_url("test-auth")

    @patch("app.infrastructure.payment.zarinpal.requests.Session.post")
    def test_create_payment_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "code": 100,
                "authority": "S00000000000000000000000000001234567",
                "fee": 0,
            },
            "errors": [],
        }
        mock_post.return_value = mock_response

        gw = ZarinPalGateway(merchant_id="test-merchant", sandbox=True)
        result = gw.create_payment(
            amount=Decimal("500000"),
            description="Test payment",
            callback_url="https://example.com/callback",
        )

        assert result.success is True
        assert result.authority == "S00000000000000000000000000001234567"
        assert "S00000000000000000000000000001234567" in result.payment_url

    @patch("app.infrastructure.payment.zarinpal.requests.Session.post")
    def test_create_payment_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {"code": -1},
            "errors": [{"code": -1, "message": "Incomplete data"}],
        }
        mock_post.return_value = mock_response

        gw = ZarinPalGateway(merchant_id="test-merchant", sandbox=True)
        result = gw.create_payment(
            amount=Decimal("500000"),
            description="Test payment",
            callback_url="https://example.com/callback",
        )

        assert result.success is False
        assert result.error_code == -1

    @patch("app.infrastructure.payment.zarinpal.requests.Session.post")
    def test_create_payment_network_error(self, mock_post):
        import requests as req_lib

        mock_post.side_effect = req_lib.ConnectionError("Connection refused")

        gw = ZarinPalGateway(merchant_id="test-merchant", sandbox=True)
        result = gw.create_payment(
            amount=Decimal("500000"),
            description="Test payment",
            callback_url="https://example.com/callback",
        )

        assert result.success is False
        assert "Connection error" in result.error

    @patch("app.infrastructure.payment.zarinpal.requests.Session.post")
    def test_verify_payment_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "code": 100,
                "ref_id": 123456789,
                "card_pan": "6210-****-****-1234",
                "fee": 0,
            },
            "errors": [],
        }
        mock_post.return_value = mock_response

        gw = ZarinPalGateway(merchant_id="test-merchant", sandbox=True)
        result = gw.verify_payment(
            authority="S00000000000000000000000000001234567",
            amount=Decimal("500000"),
        )

        assert result.success is True
        assert result.ref_id == "123456789"

    @patch("app.infrastructure.payment.zarinpal.requests.Session.post")
    def test_verify_payment_already_verified(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "code": 101,
                "ref_id": 123456789,
                "card_pan": "6210-****-****-1234",
            },
            "errors": [],
        }
        mock_post.return_value = mock_response

        gw = ZarinPalGateway(merchant_id="test-merchant", sandbox=True)
        result = gw.verify_payment(
            authority="S00000000000000000000000000001234567",
            amount=Decimal("500000"),
        )

        assert result.success is True

    @patch("app.infrastructure.payment.zarinpal.requests.Session.post")
    def test_verify_payment_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {"code": -1},
            "errors": [{"code": -1, "message": "Invalid data"}],
        }
        mock_post.return_value = mock_response

        gw = ZarinPalGateway(merchant_id="test-merchant", sandbox=True)
        result = gw.verify_payment(
            authority="S00000000000000000000000000001234567",
            amount=Decimal("500000"),
        )

        assert result.success is False


# ---------------------------------------------------------------------------
# NullPaymentGateway Tests
# ---------------------------------------------------------------------------


class TestNullPaymentGateway:
    """Tests for the null (fallback) payment gateway."""

    def test_name(self):
        gw = NullPaymentGateway()
        assert gw.name == "null"

    def test_create_payment_fails(self):
        gw = NullPaymentGateway()
        result = gw.create_payment(
            amount=Decimal("100000"),
            description="Test",
            callback_url="https://example.com",
        )
        assert result.success is False
        assert "No payment gateway" in result.error

    def test_verify_payment_fails(self):
        gw = NullPaymentGateway()
        result = gw.verify_payment(
            authority="test",
            amount=Decimal("100000"),
        )
        assert result.success is False


# ---------------------------------------------------------------------------
# Payment Service Tests
# ---------------------------------------------------------------------------


class TestPaymentService:
    """Tests for the payment application service."""

    def test_initiate_payment_negative_amount(self, db, student):
        with pytest.raises(payment_service.PaymentError, match="مبلغ"):
            payment_service.initiate_online_payment(
                student_user_id=student.id,
                amount=Decimal("-1000"),
                description="Test",
                callback_url="https://example.com",
            )

    def test_initiate_payment_zero_amount(self, db, student):
        with pytest.raises(payment_service.PaymentError, match="مبلغ"):
            payment_service.initiate_online_payment(
                student_user_id=student.id,
                amount=Decimal("0"),
                description="Test",
                callback_url="https://example.com",
            )

    def test_initiate_payment_non_student(self, db):
        user = UserModel(login="nonstudent")
        user.set_password("pass123")
        db.session.add(user)
        db.session.commit()

        with pytest.raises(payment_service.PaymentError, match="دانش‌آموز"):
            payment_service.initiate_online_payment(
                student_user_id=user.id,
                amount=Decimal("100000"),
                description="Test",
                callback_url="https://example.com",
            )

    @patch("app.application.finance.payment_service._get_gateway")
    def test_initiate_payment_gateway_error(self, mock_get_gateway, db, student):
        mock_gateway = MagicMock()
        mock_gateway.create_payment.return_value = PaymentRequestResult(
            success=False,
            error="Gateway error",
            error_code=-1,
        )
        mock_get_gateway.return_value = mock_gateway

        with pytest.raises(payment_service.PaymentError, match="خطا"):
            payment_service.initiate_online_payment(
                student_user_id=student.id,
                amount=Decimal("100000"),
                description="Test",
                callback_url="https://example.com",
            )

    @patch("app.application.finance.payment_service._get_gateway")
    def test_initiate_payment_success(self, mock_get_gateway, db, student):
        mock_gateway = MagicMock()
        mock_gateway.create_payment.return_value = PaymentRequestResult(
            success=True,
            authority="S00000000000000000000000000001234567",
            payment_url="https://sandbox.zarinpal.com/pg/StartPay/S00000000000000000000000000001234567",
        )
        mock_get_gateway.return_value = mock_gateway

        result = payment_service.initiate_online_payment(
            student_user_id=student.id,
            amount=Decimal("100000"),
            description="Test payment",
            callback_url="https://example.com/callback",
        )

        assert "transaction_id" in result
        assert "payment_url" in result
        assert "sandbox.zarinpal.com" in result["payment_url"]

        # Verify the PENDING transaction was created
        tx = FinancialTransactionModel.query.get(result["transaction_id"])
        assert tx is not None
        assert tx.status == "PENDING"
        assert tx.payment_method == "ONLINE"
        assert tx.amount == Decimal("100000")
        assert tx.reference_number == "S00000000000000000000000000001234567"

    @patch("app.application.finance.payment_service._get_gateway")
    def test_process_callback_success(self, mock_get_gateway, db, student):
        # Create a PENDING transaction
        tx = FinancialTransactionModel(
            student_user_id=student.id,
            amount=Decimal("100000"),
            transaction_type="PAYMENT",
            category="OTHER",
            description="Test",
            reference_number="S00000000000000000000000000001234567",
            payment_method="ONLINE",
            status="PENDING",
        )
        db.session.add(tx)
        db.session.commit()

        # Mock the gateway verify
        mock_gateway = MagicMock()
        mock_gateway.verify_payment.return_value = PaymentVerificationResult(
            success=True,
            ref_id="123456789",
        )
        mock_get_gateway.return_value = mock_gateway

        result = payment_service.process_payment_callback(
            authority="S00000000000000000000000000001234567",
            amount=Decimal("100000"),
            callback_status="OK",
        )

        assert result["success"] is True
        assert result["ref_id"] == "123456789"

        # Verify transaction is now ACTIVE
        tx_updated = FinancialTransactionModel.query.get(tx.id)
        assert tx_updated.status == "ACTIVE"
        assert tx_updated.reference_number == "123456789"

    @patch("app.application.finance.payment_service._get_gateway")
    def test_process_callback_user_cancelled(self, mock_get_gateway, db, student):
        # Create a PENDING transaction
        tx = FinancialTransactionModel(
            student_user_id=student.id,
            amount=Decimal("100000"),
            transaction_type="PAYMENT",
            category="OTHER",
            description="Test",
            reference_number="S00000000000000000000000000009999999",
            payment_method="ONLINE",
            status="PENDING",
        )
        db.session.add(tx)
        db.session.commit()

        result = payment_service.process_payment_callback(
            authority="S00000000000000000000000000009999999",
            amount=Decimal("100000"),
            callback_status="NOK",
        )

        assert result["success"] is False
        assert "لغو" in result["message"]

        # Verify transaction is now FAILED
        tx_updated = FinancialTransactionModel.query.get(tx.id)
        assert tx_updated.status == "FAILED"

    @patch("app.application.finance.payment_service._get_gateway")
    def test_process_callback_unknown_authority(self, mock_get_gateway, db):
        result = payment_service.process_payment_callback(
            authority="UNKNOWN_AUTHORITY",
            amount=Decimal("100000"),
            callback_status="OK",
        )

        assert result["success"] is False
        assert result["transaction_id"] is None


# ---------------------------------------------------------------------------
# Balance Impact Tests
# ---------------------------------------------------------------------------


class TestOnlinePaymentBalance:
    """Tests that online payments correctly affect student balance."""

    def test_pending_payment_does_not_affect_balance(self, db, student_with_debt):
        """A PENDING payment should not change the balance."""
        student_id = student_with_debt.id
        balance_before = finance_service.get_student_balance(student_id)
        assert balance_before == Decimal("-500000")

        # Create a PENDING payment
        tx = FinancialTransactionModel(
            student_user_id=student_id,
            amount=Decimal("200000"),
            transaction_type="PAYMENT",
            category="OTHER",
            description="Pending payment",
            reference_number="S-PENDING-123",
            payment_method="ONLINE",
            status="PENDING",
        )
        db.session.add(tx)
        db.session.commit()

        balance_after_pending = finance_service.get_student_balance(student_id)
        assert balance_after_pending == Decimal("-500000")

    def test_active_payment_reduces_debt(self, db, student_with_debt):
        """An ACTIVE payment should reduce the student's debt."""
        student_id = student_with_debt.id
        balance_before = finance_service.get_student_balance(student_id)
        assert balance_before == Decimal("-500000")

        # Create an ACTIVE payment
        tx = FinancialTransactionModel(
            student_user_id=student_id,
            amount=Decimal("200000"),
            transaction_type="PAYMENT",
            category="OTHER",
            description="Completed payment",
            reference_number="S-COMPLETE-123",
            payment_method="ONLINE",
            status="ACTIVE",
        )
        db.session.add(tx)
        db.session.commit()

        balance_after = finance_service.get_student_balance(student_id)
        assert balance_after == Decimal("-300000")

    def test_full_payment_clears_debt(self, db, student_with_debt):
        """A full payment should bring balance to zero."""
        student_id = student_with_debt.id

        tx = FinancialTransactionModel(
            student_user_id=student_id,
            amount=Decimal("500000"),
            transaction_type="PAYMENT",
            category="OTHER",
            description="Full payment",
            reference_number="S-FULL-123",
            payment_method="ONLINE",
            status="ACTIVE",
        )
        db.session.add(tx)
        db.session.commit()

        balance_after = finance_service.get_student_balance(student_id)
        assert balance_after == Decimal("0")

    def test_failed_payment_does_not_affect_balance(self, db, student_with_debt):
        """A FAILED payment should not change the balance."""
        student_id = student_with_debt.id
        balance_before = finance_service.get_student_balance(student_id)

        tx = FinancialTransactionModel(
            student_user_id=student_id,
            amount=Decimal("200000"),
            transaction_type="PAYMENT",
            category="OTHER",
            description="Failed payment",
            reference_number="S-FAILED-123",
            payment_method="ONLINE",
            status="FAILED",
        )
        db.session.add(tx)
        db.session.commit()

        balance_after = finance_service.get_student_balance(student_id)
        assert balance_after == balance_before


# ---------------------------------------------------------------------------
# Route Tests (with mocked gateway)
# ---------------------------------------------------------------------------


class TestPaymentRoutes:
    """Tests for the online payment web routes."""

    def _login(self, client, user):
        """Helper to log in a user."""
        client.post(
            "/auth/login",
            data={"login": user.login, "password": "pass123"},
            follow_redirects=True,
        )

    @patch("app.application.finance.payment_service._get_gateway")
    def test_student_pay_online_redirects_to_gateway(
        self, mock_get_gateway, client, db, student_with_debt
    ):
        """Test that initiating payment redirects to ZarinPal."""
        mock_gateway = MagicMock()
        mock_gateway.create_payment.return_value = PaymentRequestResult(
            success=True,
            authority="S00000000000000000000000000001234567",
            payment_url="https://sandbox.zarinpal.com/pg/StartPay/S00000000000000000000000000001234567",
        )
        mock_get_gateway.return_value = mock_gateway

        self._login(client, student_with_debt)

        response = client.post(
            "/finance/student/pay",
            data={"amount": "200000"},
            follow_redirects=False,
        )

        # Should redirect to ZarinPal
        assert response.status_code == 302
        assert "sandbox.zarinpal.com" in response.headers["Location"]

    def test_student_pay_online_invalid_amount(self, client, db, student_with_debt):
        """Test that invalid amount shows error flash."""
        self._login(client, student_with_debt)

        response = client.post(
            "/finance/student/pay",
            data={"amount": "invalid"},
            follow_redirects=True,
        )

        assert response.status_code == 200

    @patch("app.application.finance.payment_service._get_gateway")
    def test_payment_callback_success(
        self, mock_get_gateway, client, db, student_with_debt
    ):
        """Test the payment callback route with a successful payment."""
        # Create a PENDING transaction
        tx = FinancialTransactionModel(
            student_user_id=student_with_debt.id,
            amount=Decimal("200000"),
            transaction_type="PAYMENT",
            category="OTHER",
            description="Test",
            reference_number="S00000000000000000000000000001234567",
            payment_method="ONLINE",
            status="PENDING",
        )
        db.session.add(tx)
        db.session.commit()

        mock_gateway = MagicMock()
        mock_gateway.verify_payment.return_value = PaymentVerificationResult(
            success=True,
            ref_id="987654321",
        )
        mock_get_gateway.return_value = mock_gateway

        response = client.get(
            "/finance/payment/callback?Authority=S00000000000000000000000000001234567&Status=OK",
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verify transaction is now ACTIVE
        tx_updated = FinancialTransactionModel.query.get(tx.id)
        assert tx_updated.status == "ACTIVE"

    def test_payment_callback_cancelled(self, client, db, student_with_debt):
        """Test the payment callback route when user cancels."""
        tx = FinancialTransactionModel(
            student_user_id=student_with_debt.id,
            amount=Decimal("200000"),
            transaction_type="PAYMENT",
            category="OTHER",
            description="Test",
            reference_number="S00000000000000000000000000009999999",
            payment_method="ONLINE",
            status="PENDING",
        )
        db.session.add(tx)
        db.session.commit()

        response = client.get(
            "/finance/payment/callback?Authority=S00000000000000000000000000009999999&Status=NOK",
            follow_redirects=True,
        )

        assert response.status_code == 200

        tx_updated = FinancialTransactionModel.query.get(tx.id)
        assert tx_updated.status == "FAILED"

    def test_payment_callback_no_authority(self, client, db):
        """Test the payment callback with missing authority."""
        response = client.get(
            "/finance/payment/callback",
            follow_redirects=True,
        )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Domain Entity Tests
# ---------------------------------------------------------------------------


class TestTransactionStatusExtended:
    """Tests for the extended TransactionStatus enum."""

    def test_pending_status(self):
        from app.domain.finance import TransactionStatus

        assert TransactionStatus.PENDING == "PENDING"

    def test_failed_status(self):
        from app.domain.finance import TransactionStatus

        assert TransactionStatus.FAILED == "FAILED"

    def test_pending_is_not_active(self):
        tx = FinancialTransactionModel(
            student_user_id=1,
            amount=Decimal("100"),
            transaction_type="PAYMENT",
            category="OTHER",
            status="PENDING",
        )
        # The domain entity check
        assert tx.status != "ACTIVE"
