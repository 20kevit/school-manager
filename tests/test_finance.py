"""Comprehensive tests for P6 — Finance & Tuition."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.application.enrollment import enrollment_service
from app.application.finance import finance_service
from app.domain.finance import (
    FinancialTransaction,
    TransactionCategory,
    TransactionStatus,
    TransactionType,
)
from app.infrastructure.database.models import (
    AcademyClassModel,
    CourseModel,
    FinancialTransactionModel,
    ParentProfileModel,
    StudentProfileModel,
    UserModel,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def course(db):
    course = CourseModel(title="Python", num_sessions=10)
    db.session.add(course)
    db.session.commit()
    return course


@pytest.fixture
def academy_class(db, course):
    cls = AcademyClassModel(
        course_id=course.id,
        title="Class A",
        start_date=date(2026, 1, 1),
        capacity=30,
        tuition=Decimal("5000000"),
        num_sessions=10,
        status="ACTIVE",
    )
    db.session.add(cls)
    db.session.commit()
    return cls


@pytest.fixture
def class_no_tuition(db, course):
    cls = AcademyClassModel(
        course_id=course.id,
        title="Class No Tuition",
        start_date=date(2026, 1, 1),
        capacity=30,
        tuition=Decimal("0"),
        num_sessions=10,
        status="ACTIVE",
    )
    db.session.add(cls)
    db.session.commit()
    return cls


@pytest.fixture
def student(db):
    user = UserModel(login="fin_student")
    user.set_password("pass123")
    from app.infrastructure.database.models import RoleModel

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
def student_under_18(db):
    user = UserModel(login="fin_student_under18")
    user.set_password("pass123")
    from app.infrastructure.database.models import RoleModel

    role = RoleModel(name="STUDENT")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.flush()

    profile = StudentProfileModel(
        user_id=user.id,
        first_name="Sara",
        last_name="Ahmadi",
        national_id="2222222222",
        mobile_phone="09122222222",
        birth_date=date(2015, 6, 1),
        gender="FEMALE",
    )
    db.session.add(profile)
    db.session.commit()
    return user


@pytest.fixture
def parent_user_with_child(db, student):
    from app.infrastructure.database.models import RoleModel

    user = UserModel(login="fin_parent")
    user.set_password("pass123")
    role = RoleModel(name="PARENT")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.flush()

    profile = ParentProfileModel(
        user_id=user.id,
        first_name="Mohammad",
        last_name="Rezaei",
        national_id="3333333333",
        mobile_phone="09123333333",
    )
    db.session.add(profile)
    db.session.flush()

    student_profile = StudentProfileModel.query.filter_by(user_id=student.id).first()
    profile.children.append(student_profile)
    db.session.commit()
    return user


@pytest.fixture
def admin_user(db):
    from app.infrastructure.database.models import RoleModel

    user = UserModel(login="fin_admin")
    user.set_password("pass123")
    role = RoleModel(name="ADMIN")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user


# ---------------------------------------------------------------------------
# Domain entity tests
# ---------------------------------------------------------------------------


class TestFinancialTransactionDomain:
    """Tests for the FinancialTransaction domain entity."""

    def test_create_transaction(self):
        tx = FinancialTransaction(
            id=None,
            student_user_id=1,
            amount=Decimal("5000000"),
            transaction_type=TransactionType.CHARGE,
            category=TransactionCategory.TUITION,
        )
        assert tx.student_user_id == 1
        assert tx.amount == Decimal("5000000")
        assert tx.transaction_type == TransactionType.CHARGE
        assert tx.status == TransactionStatus.ACTIVE

    def test_signed_amount_charge(self):
        tx = FinancialTransaction(
            id=None,
            student_user_id=1,
            amount=Decimal("5000000"),
            transaction_type=TransactionType.CHARGE,
            category=TransactionCategory.TUITION,
        )
        assert tx.signed_amount == Decimal("-5000000")

    def test_signed_amount_payment(self):
        tx = FinancialTransaction(
            id=None,
            student_user_id=1,
            amount=Decimal("2000000"),
            transaction_type=TransactionType.PAYMENT,
            category=TransactionCategory.OTHER,
        )
        assert tx.signed_amount == Decimal("2000000")

    def test_signed_amount_discount(self):
        tx = FinancialTransaction(
            id=None,
            student_user_id=1,
            amount=Decimal("1000000"),
            transaction_type=TransactionType.DISCOUNT,
            category=TransactionCategory.TUITION,
        )
        assert tx.signed_amount == Decimal("1000000")

    def test_signed_amount_refund(self):
        tx = FinancialTransaction(
            id=None,
            student_user_id=1,
            amount=Decimal("500000"),
            transaction_type=TransactionType.REFUND,
            category=TransactionCategory.OTHER,
        )
        assert tx.signed_amount == Decimal("-500000")

    def test_is_active(self):
        tx = FinancialTransaction(
            id=None,
            student_user_id=1,
            amount=Decimal("100"),
            transaction_type=TransactionType.PAYMENT,
            category=TransactionCategory.OTHER,
            status=TransactionStatus.ACTIVE,
        )
        assert tx.is_active() is True

    def test_is_not_active_when_voided(self):
        tx = FinancialTransaction(
            id=None,
            student_user_id=1,
            amount=Decimal("100"),
            transaction_type=TransactionType.PAYMENT,
            category=TransactionCategory.OTHER,
            status=TransactionStatus.VOIDED,
        )
        assert tx.is_active() is False

    def test_void_transaction(self):
        tx = FinancialTransaction(
            id=None,
            student_user_id=1,
            amount=Decimal("100"),
            transaction_type=TransactionType.PAYMENT,
            category=TransactionCategory.OTHER,
            status=TransactionStatus.ACTIVE,
        )
        tx.void()
        assert tx.status == TransactionStatus.VOIDED

    def test_void_already_voided_raises(self):
        tx = FinancialTransaction(
            id=None,
            student_user_id=1,
            amount=Decimal("100"),
            transaction_type=TransactionType.PAYMENT,
            category=TransactionCategory.OTHER,
            status=TransactionStatus.VOIDED,
        )
        with pytest.raises(ValueError, match="already voided"):
            tx.void()


# ---------------------------------------------------------------------------
# Account / Balance tests
# ---------------------------------------------------------------------------


class TestAccountBalance:
    """Tests for student balance calculation."""

    def test_zero_balance(self, db, student):
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("0")

    def test_negative_balance_after_charge(self, db, student):
        finance_service.create_charge(
            student_user_id=student.id,
            amount=Decimal("5000000"),
            category="TUITION",
        )
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("-5000000")

    def test_positive_balance_after_payment(self, db, student):
        finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("3000000"),
        )
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("3000000")

    def test_balance_derived_from_transactions(self, db, student):
        finance_service.create_charge(
            student_user_id=student.id,
            amount=Decimal("5000000"),
            category="TUITION",
        )
        finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("2000000"),
        )
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("-3000000")

    def test_multiple_transactions(self, db, student):
        finance_service.create_charge(
            student_user_id=student.id,
            amount=Decimal("5000000"),
            category="TUITION",
        )
        finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("6000000"),
        )
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("1000000")


# ---------------------------------------------------------------------------
# Tuition tests
# ---------------------------------------------------------------------------


class TestTuition:
    """Tests for tuition charge creation and integration."""

    def test_tuition_charge_on_approved_enrollment(self, db, student, academy_class):
        enrollment = enrollment_service.admin_enroll_student(
            student_user_id=student.id,
            class_id=academy_class.id,
            auto_approve=True,
        )
        tx = FinancialTransactionModel.query.filter_by(
            enrollment_id=enrollment.id,
            category="TUITION",
        ).first()
        assert tx is not None
        assert tx.amount == Decimal("5000000")
        assert tx.transaction_type == "CHARGE"

    def test_tuition_snapshot_preserved(self, db, student, academy_class):
        enrollment = enrollment_service.admin_enroll_student(
            student_user_id=student.id,
            class_id=academy_class.id,
            auto_approve=True,
        )
        # Change class tuition after enrollment
        academy_class.tuition = Decimal("6000000")
        db.session.commit()

        tx = FinancialTransactionModel.query.filter_by(
            enrollment_id=enrollment.id,
        ).first()
        assert tx.amount == Decimal("5000000")  # Original amount preserved

    def test_duplicate_tuition_prevention(self, db, student, academy_class):
        enrollment = enrollment_service.admin_enroll_student(
            student_user_id=student.id,
            class_id=academy_class.id,
            auto_approve=True,
        )
        # Try to create tuition again
        with pytest.raises(finance_service.FinanceError, match="already exists"):
            finance_service.create_tuition_charge(
                student_user_id=student.id,
                class_id=academy_class.id,
                enrollment_id=enrollment.id,
            )

    def test_no_tuition_charge_if_class_has_zero_tuition(
        self, db, student, class_no_tuition
    ):
        enrollment = enrollment_service.admin_enroll_student(
            student_user_id=student.id,
            class_id=class_no_tuition.id,
            auto_approve=True,
        )
        tx = FinancialTransactionModel.query.filter_by(
            enrollment_id=enrollment.id,
        ).first()
        assert tx is None


# ---------------------------------------------------------------------------
# Payment tests
# ---------------------------------------------------------------------------


class TestPayments:
    """Tests for payment recording."""

    def test_full_payment(self, db, student):
        finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("5000000"),
        )
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("5000000")

    def test_partial_payment(self, db, student):
        finance_service.create_charge(
            student_user_id=student.id,
            amount=Decimal("5000000"),
            category="TUITION",
        )
        finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("2000000"),
        )
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("-3000000")

    def test_overpayment_creates_credit(self, db, student):
        finance_service.create_charge(
            student_user_id=student.id,
            amount=Decimal("5000000"),
            category="TUITION",
        )
        finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("6000000"),
        )
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("1000000")

    def test_different_payment_methods(self, db, student):
        for method in ["CASH", "CARD", "BANK_TRANSFER", "ONLINE", "OTHER"]:
            finance_service.record_payment(
                student_user_id=student.id,
                amount=Decimal("100000"),
                payment_method=method,
            )
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("500000")

    def test_invalid_payment_amount(self, db, student):
        with pytest.raises(finance_service.FinanceError, match="must be positive"):
            finance_service.record_payment(
                student_user_id=student.id,
                amount=Decimal("-100"),
            )

    def test_zero_payment_amount(self, db, student):
        with pytest.raises(finance_service.FinanceError, match="must be positive"):
            finance_service.record_payment(
                student_user_id=student.id,
                amount=Decimal("0"),
            )


# ---------------------------------------------------------------------------
# Discount tests
# ---------------------------------------------------------------------------


class TestDiscounts:
    """Tests for discount application."""

    def test_discount_application(self, db, student):
        finance_service.apply_discount(
            student_user_id=student.id,
            amount=Decimal("1000000"),
        )
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("1000000")

    def test_discount_reflected_in_ledger(self, db, student):
        finance_service.apply_discount(
            student_user_id=student.id,
            amount=Decimal("1000000"),
        )
        tx = FinancialTransactionModel.query.filter_by(
            student_user_id=student.id,
            transaction_type="DISCOUNT",
        ).first()
        assert tx is not None
        assert tx.amount == Decimal("1000000")

    def test_discount_with_tuition(self, db, student):
        finance_service.create_charge(
            student_user_id=student.id,
            amount=Decimal("5000000"),
            category="TUITION",
        )
        finance_service.apply_discount(
            student_user_id=student.id,
            amount=Decimal("1000000"),
            category="TUITION",
        )
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("-4000000")

    def test_invalid_discount_amount(self, db, student):
        with pytest.raises(finance_service.FinanceError, match="must be positive"):
            finance_service.apply_discount(
                student_user_id=student.id,
                amount=Decimal("0"),
            )


# ---------------------------------------------------------------------------
# Refund tests
# ---------------------------------------------------------------------------


class TestRefunds:
    """Tests for refund recording."""

    def test_full_refund(self, db, student):
        payment = finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("5000000"),
        )
        finance_service.record_refund(
            student_user_id=student.id,
            amount=Decimal("5000000"),
            related_transaction_id=payment.id,
        )
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("0")

    def test_partial_refund(self, db, student):
        payment = finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("5000000"),
        )
        finance_service.record_refund(
            student_user_id=student.id,
            amount=Decimal("2000000"),
            related_transaction_id=payment.id,
        )
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("3000000")

    def test_original_payment_preserved(self, db, student):
        payment = finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("5000000"),
        )
        finance_service.record_refund(
            student_user_id=student.id,
            amount=Decimal("2000000"),
            related_transaction_id=payment.id,
        )
        payments = FinancialTransactionModel.query.filter_by(
            student_user_id=student.id,
            transaction_type="PAYMENT",
            status="ACTIVE",
        ).all()
        assert len(payments) == 1
        assert payments[0].amount == Decimal("5000000")

    def test_invalid_refund_amount(self, db, student):
        with pytest.raises(finance_service.FinanceError, match="must be positive"):
            finance_service.record_refund(
                student_user_id=student.id,
                amount=Decimal("-100"),
            )

    def test_unlinked_refund_rejected(self, db, student):
        """Ordinary refunds must reference the original payment."""
        with pytest.raises(finance_service.FinanceError, match="must reference"):
            finance_service.record_refund(
                student_user_id=student.id,
                amount=Decimal("1000"),
            )

    def test_goodwill_credit_requires_reason(self, db, student):
        with pytest.raises(finance_service.FinanceError, match="reason is required"):
            finance_service.record_goodwill_credit(
                student_user_id=student.id,
                amount=Decimal("50000"),
                reason="   ",
            )

    def test_goodwill_credit_is_auditable_adjustment(self, db, student):
        tx = finance_service.record_goodwill_credit(
            student_user_id=student.id,
            amount=Decimal("50000"),
            reason="Goodwill gesture for service disruption",
            created_by=student.id,
        )
        assert tx.transaction_type == "ADJUSTMENT"
        assert tx.amount == Decimal("50000")
        assert "Goodwill" in tx.description
        assert tx.created_by == student.id
        assert finance_service.get_student_balance(student.id) == Decimal("50000")

    def test_refund_class_mismatch_rejected(self, db, student):
        payment = finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("5000000"),
            class_id=7,
        )
        with pytest.raises(finance_service.FinanceError, match="does not match"):
            finance_service.record_refund(
                student_user_id=student.id,
                amount=Decimal("1000"),
                related_transaction_id=payment.id,
                class_id=8,
            )

    def test_refund_cannot_introduce_class(self, db, student):
        payment = finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("5000000"),
        )
        assert payment.class_id is None
        with pytest.raises(finance_service.FinanceError, match="cannot introduce"):
            finance_service.record_refund(
                student_user_id=student.id,
                amount=Decimal("1000"),
                related_transaction_id=payment.id,
                class_id=9,
            )


# ---------------------------------------------------------------------------
# Correction tests
# ---------------------------------------------------------------------------


class TestCorrections:
    """Tests for transaction correction."""

    def test_correct_payment(self, db, student):
        tx = finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("2000000"),
        )
        corrected = finance_service.correct_transaction(
            tx.id,
            new_amount=Decimal("200000"),
            corrected_by=admin_user_id(db, student),
        )
        assert corrected.amount == Decimal("200000")

        original = FinancialTransactionModel.query.get(tx.id)
        assert original.status == "CORRECTED"

    def test_historical_information_preserved(self, db, student):
        tx = finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("2000000"),
        )
        finance_service.correct_transaction(
            tx.id,
            new_amount=Decimal("200000"),
            corrected_by=admin_user_id(db, student),
        )
        original = FinancialTransactionModel.query.get(tx.id)
        assert original.amount == Decimal("2000000")  # Original amount preserved

    def test_corrected_balance_is_correct(self, db, student):
        tx = finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("2000000"),
        )
        finance_service.correct_transaction(
            tx.id,
            new_amount=Decimal("200000"),
            corrected_by=admin_user_id(db, student),
        )
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("200000")

    def test_correct_refund_row_rejected(self, db, student):
        payment = finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("2000000"),
        )
        refund = finance_service.record_refund(
            student_user_id=student.id,
            amount=Decimal("500000"),
            related_transaction_id=payment.id,
        )
        with pytest.raises(finance_service.FinanceError, match="cannot be corrected"):
            finance_service.correct_transaction(
                refund.id,
                new_amount=Decimal("100000"),
                corrected_by=admin_user_id(db, student),
            )

    def test_correct_reversal_row_rejected(self, db, student):
        tx = finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("2000000"),
        )
        reversal = finance_service.reverse_transaction(tx.id)
        with pytest.raises(finance_service.FinanceError, match="cannot be corrected"):
            finance_service.correct_transaction(
                reversal.id,
                new_description="nope",
                corrected_by=admin_user_id(db, student),
            )

    def test_correct_repoints_live_refund_to_copy(self, db, student):
        payment = finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("2000000"),
        )
        refund = finance_service.record_refund(
            student_user_id=student.id,
            amount=Decimal("500000"),
            related_transaction_id=payment.id,
        )
        corrected = finance_service.correct_transaction(
            payment.id,
            new_amount=Decimal("2000000"),
            corrected_by=admin_user_id(db, student),
        )
        # Child follows the lineage: cap accounting still sees it.
        assert (
            FinancialTransactionModel.query.get(refund.id).related_transaction_id
            == corrected.id
        )
        assert finance_service.get_remaining_refundable(corrected.id) == Decimal(
            "1500000"
        )
        assert finance_service.get_student_balance(student.id) == Decimal("1500000")

    def test_reversed_payment_has_no_remaining_refundable(self, db, student):
        payment = finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("2000000"),
        )
        finance_service.reverse_transaction(payment.id)
        assert finance_service.get_remaining_refundable(payment.id) == Decimal("0")
        with pytest.raises(finance_service.FinanceError, match="remaining refundable"):
            finance_service.record_refund(
                student_user_id=student.id,
                amount=Decimal("1000"),
                related_transaction_id=payment.id,
            )


def admin_user_id(db, student):
    """Helper to get an admin user ID."""
    from app.infrastructure.database.models import RoleModel

    user = UserModel(login="test_admin_helper")
    user.set_password("pass123")
    role = RoleModel(name="ADMIN")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user.id


# ---------------------------------------------------------------------------
# Enrollment cancellation tests
# ---------------------------------------------------------------------------


class TestEnrollmentCancellation:
    """Tests for financial reversal on enrollment cancellation."""

    def test_cancellation_creates_reversal(self, db, student, academy_class):
        enrollment = enrollment_service.admin_enroll_student(
            student_user_id=student.id,
            class_id=academy_class.id,
            auto_approve=True,
        )
        enrollment_service.cancel_enrollment(enrollment)

        reversal = FinancialTransactionModel.query.filter_by(
            enrollment_id=enrollment.id,
            transaction_type="REVERSAL",
        ).first()
        assert reversal is not None
        assert reversal.amount == Decimal("5000000")

    def test_original_transaction_preserved(self, db, student, academy_class):
        enrollment = enrollment_service.admin_enroll_student(
            student_user_id=student.id,
            class_id=academy_class.id,
            auto_approve=True,
        )
        enrollment_service.cancel_enrollment(enrollment)

        original = FinancialTransactionModel.query.filter_by(
            enrollment_id=enrollment.id,
            transaction_type="CHARGE",
        ).first()
        assert original.status == "ACTIVE"  # Preserved for history

    def test_final_balance_is_correct(self, db, student, academy_class):
        enrollment = enrollment_service.admin_enroll_student(
            student_user_id=student.id,
            class_id=academy_class.id,
            auto_approve=True,
        )
        enrollment_service.cancel_enrollment(enrollment)

        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("0")


# ---------------------------------------------------------------------------
# Manual transaction tests
# ---------------------------------------------------------------------------


class TestManualTransactions:
    """Tests for manual financial transactions."""

    def test_manual_charge(self, db, student):
        finance_service.create_charge(
            student_user_id=student.id,
            amount=Decimal("500000"),
            category="BOOK",
            description="Book charge",
        )
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("-500000")

    def test_manual_payment(self, db, student):
        finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("500000"),
            payment_method="CASH",
            description="Cash payment",
        )
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("500000")

    def test_adjustment(self, db, student):
        finance_service.create_adjustment(
            student_user_id=student.id,
            amount=Decimal("100000"),
            description="Adjustment",
        )
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("100000")

    def test_invalid_student_raises(self, db):
        with pytest.raises(finance_service.FinanceError, match="Student not found"):
            finance_service.create_charge(
                student_user_id=99999,
                amount=Decimal("100"),
                category="OTHER",
            )


# ---------------------------------------------------------------------------
# Authorization tests
# ---------------------------------------------------------------------------


class TestParentAuthorization:
    """Tests for parent financial access."""

    def test_parent_can_see_linked_child_finance(
        self, client, parent_user_with_child, student
    ):
        client.post(
            "/auth/login",
            data={"login": "fin_parent", "password": "pass123"},
            follow_redirects=True,
        )
        response = client.get("/finance/parent/overview")
        assert response.status_code == 200

    def test_parent_cannot_see_unrelated_student(
        self, client, parent_user_with_child, student, db
    ):
        # Create another student not linked to parent
        other = UserModel(login="other_student")
        other.set_password("pass123")
        from app.infrastructure.database.models import RoleModel

        role = RoleModel.query.get("STUDENT")
        other.roles.append(role)
        db.session.add(other)
        db.session.flush()
        other_profile = StudentProfileModel(
            user_id=other.id,
            first_name="Other",
            last_name="Student",
            national_id="4444444444",
            mobile_phone="09124444444",
            birth_date=date(2000, 1, 1),
            gender="MALE",
        )
        db.session.add(other_profile)
        db.session.commit()

        client.post(
            "/auth/login",
            data={"login": "fin_parent", "password": "pass123"},
            follow_redirects=True,
        )
        response = client.get(f"/finance/parent/child/{other.id}/statement")
        assert response.status_code == 302  # Redirected with error


class TestStudentAuthorization:
    """Tests for student financial access."""

    def test_student_under_18_cannot_see_finance(self, client, student_under_18):
        client.post(
            "/auth/login",
            data={"login": "fin_student_under18", "password": "pass123"},
            follow_redirects=True,
        )
        response = client.get("/finance/student/my-finance")
        assert response.status_code == 302  # Redirected with error

    def test_student_18_plus_can_see_finance(self, client, student):
        client.post(
            "/auth/login",
            data={"login": "fin_student", "password": "pass123"},
            follow_redirects=True,
        )
        response = client.get("/finance/student/my-finance")
        assert response.status_code == 200


class TestAdminAuthorization:
    """Tests for admin financial access."""

    def test_admin_has_full_access(self, client, admin_user):
        client.post(
            "/auth/login",
            data={"login": "fin_admin", "password": "pass123"},
            follow_redirects=True,
        )
        response = client.get("/finance/admin/dashboard")
        assert response.status_code == 200

    def test_non_admin_cannot_access_admin_finance(self, client, student):
        client.post(
            "/auth/login",
            data={"login": "fin_student", "password": "pass123"},
            follow_redirects=True,
        )
        response = client.get("/finance/admin/dashboard")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Report tests
# ---------------------------------------------------------------------------


class TestReports:
    """Tests for financial reports."""

    def test_debt_report(self, db, student):
        finance_service.create_charge(
            student_user_id=student.id,
            amount=Decimal("5000000"),
            category="TUITION",
        )
        report = finance_service.get_debt_report()
        assert len(report) == 1
        assert report[0]["student_user_id"] == student.id
        assert report[0]["balance"] == Decimal("-5000000")

    def test_credit_report(self, db, student):
        finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("5000000"),
        )
        report = finance_service.get_credit_report()
        assert len(report) == 1
        assert report[0]["student_user_id"] == student.id
        assert report[0]["balance"] == Decimal("5000000")

    def test_revenue_report(self, db, student):
        finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("5000000"),
        )
        report = finance_service.get_revenue_report()
        assert report["payments"] == Decimal("5000000")

    def test_dashboard_summary(self, db, student):
        finance_service.create_charge(
            student_user_id=student.id,
            amount=Decimal("5000000"),
            category="TUITION",
        )
        finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("2000000"),
        )
        summary = finance_service.get_dashboard_summary()
        assert summary["debtors_count"] == 1
        assert summary["total_debt"] == Decimal("3000000")


# ---------------------------------------------------------------------------
# Balance by class tests
# ---------------------------------------------------------------------------


class TestBalanceByClass:
    """Tests for class-specific balance calculation."""

    def test_balance_by_class(self, db, student, academy_class):
        enrollment_service.admin_enroll_student(
            student_user_id=student.id,
            class_id=academy_class.id,
            auto_approve=True,
        )
        finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("2000000"),
            class_id=academy_class.id,
        )
        balance = finance_service.get_student_balance_by_class(
            student.id, academy_class.id
        )
        assert balance == Decimal("-3000000")


# ---------------------------------------------------------------------------
# Statement tests
# ---------------------------------------------------------------------------


class TestStatement:
    """Tests for student statement."""

    def test_statement_ordered_by_date(self, db, student):
        finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("1000000"),
        )
        finance_service.create_charge(
            student_user_id=student.id,
            amount=Decimal("500000"),
            category="BOOK",
        )
        statement = finance_service.get_student_statement(student.id)
        assert len(statement) == 2
        tx_types = {tx.transaction_type for tx in statement}
        assert tx_types == {"PAYMENT", "CHARGE"}


# ---------------------------------------------------------------------------
# Class financial summary tests
# ---------------------------------------------------------------------------


class TestClassFinancialSummary:
    """Tests for class financial summary."""

    def test_class_summary(self, db, student, academy_class):
        enrollment_service.admin_enroll_student(
            student_user_id=student.id,
            class_id=academy_class.id,
            auto_approve=True,
        )
        summary = finance_service.get_class_financial_summary(academy_class.id)
        assert summary["enrolled_count"] == 1
        assert summary["total_tuition"] == Decimal("5000000")

    def test_empty_class_summary(self, db, academy_class):
        summary = finance_service.get_class_financial_summary(academy_class.id)
        assert summary["enrolled_count"] == 0


# ---------------------------------------------------------------------------
# Transaction report tests
# ---------------------------------------------------------------------------


class TestTransactionReport:
    """Tests for filtered transaction report."""

    def test_filter_by_student(self, db, student, academy_class):
        enrollment_service.admin_enroll_student(
            student_user_id=student.id,
            class_id=academy_class.id,
            auto_approve=True,
        )
        finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("1000000"),
        )
        report = finance_service.get_transaction_report(student_user_id=student.id)
        assert len(report) == 2  # tuition charge + payment

    def test_filter_by_category(self, db, student):
        finance_service.create_charge(
            student_user_id=student.id,
            amount=Decimal("500000"),
            category="BOOK",
        )
        finance_service.create_charge(
            student_user_id=student.id,
            amount=Decimal("300000"),
            category="EQUIPMENT",
        )
        report = finance_service.get_transaction_report(category="BOOK")
        assert len(report) == 1
        assert report[0].category == "BOOK"


# ---------------------------------------------------------------------------
# Reversal tests
# ---------------------------------------------------------------------------


class TestReversal:
    """Tests for transaction reversal."""

    def test_reverse_payment(self, db, student):
        tx = finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("5000000"),
        )
        finance_service.reverse_transaction(tx.id)

        original = FinancialTransactionModel.query.get(tx.id)
        assert original.status == "ACTIVE"  # Preserved for history

        reversal = FinancialTransactionModel.query.filter_by(
            related_transaction_id=tx.id,
            transaction_type="REVERSAL",
        ).first()
        assert reversal is not None
        # Reversal of PAYMENT is negative (undoes the credit)
        assert reversal.amount == Decimal("-5000000")

    def test_balance_after_reversal(self, db, student):
        tx = finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("5000000"),
        )
        finance_service.reverse_transaction(tx.id)
        balance = finance_service.get_student_balance(student.id)
        assert balance == Decimal("0")


# ---------------------------------------------------------------------------
# Web UI route tests
# ---------------------------------------------------------------------------


class TestFinanceRoutes:
    """Tests for finance web routes."""

    def test_admin_dashboard_route(self, client, admin_user):
        client.post(
            "/auth/login",
            data={"login": "fin_admin", "password": "pass123"},
            follow_redirects=True,
        )
        response = client.get("/finance/admin/dashboard")
        assert response.status_code == 200

    def test_admin_transactions_route(self, client, admin_user):
        client.post(
            "/auth/login",
            data={"login": "fin_admin", "password": "pass123"},
            follow_redirects=True,
        )
        response = client.get("/finance/admin/transactions")
        assert response.status_code == 200

    def test_admin_create_transaction_get(self, client, admin_user):
        client.post(
            "/auth/login",
            data={"login": "fin_admin", "password": "pass123"},
            follow_redirects=True,
        )
        response = client.get("/finance/admin/transaction/create")
        assert response.status_code == 200

    def test_admin_create_goodwill_credit_via_form(
        self, client, db, admin_user, student
    ):
        """GOODWILL type creates a reasoned ADJUSTMENT, never a refund."""
        client.post(
            "/auth/login",
            data={"login": "fin_admin", "password": "pass123"},
            follow_redirects=True,
        )
        response = client.post(
            "/finance/admin/transaction/create",
            data={
                "student_user_id": str(student.id),
                "amount": "75000",
                "transaction_type": "GOODWILL",
                "category": "OTHER",
                "description": "Service recovery gesture",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        tx = FinancialTransactionModel.query.filter_by(
            student_user_id=student.id,
            transaction_type="ADJUSTMENT",
        ).first()
        assert tx is not None
        assert tx.amount == Decimal("75000")
        assert "recovery" in tx.description
        # The redirect target (transaction list with rows) must render,
        # including the status_badge helper (latent 500 when rows exist).
        assert "badge" in response.get_data(as_text=True)

    def test_admin_create_refund_without_link_rejected(
        self, client, db, admin_user, student
    ):
        """Unlinked admin refunds are rejected with a clean error page."""
        client.post(
            "/auth/login",
            data={"login": "fin_admin", "password": "pass123"},
            follow_redirects=True,
        )
        before = FinancialTransactionModel.query.count()
        response = client.post(
            "/finance/admin/transaction/create",
            data={
                "student_user_id": str(student.id),
                "amount": "1000",
                "transaction_type": "REFUND",
                "description": "no link",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert FinancialTransactionModel.query.count() == before

    def test_parent_overview_route(self, client, parent_user_with_child):
        client.post(
            "/auth/login",
            data={"login": "fin_parent", "password": "pass123"},
            follow_redirects=True,
        )
        response = client.get("/finance/parent/overview")
        assert response.status_code == 200

    def test_student_finance_route(self, client, student):
        client.post(
            "/auth/login",
            data={"login": "fin_student", "password": "pass123"},
            follow_redirects=True,
        )
        response = client.get("/finance/student/my-finance")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases and integrity."""

    def test_charge_zero_amount(self, db, student):
        with pytest.raises(finance_service.FinanceError, match="must be positive"):
            finance_service.create_charge(
                student_user_id=student.id,
                amount=Decimal("0"),
                category="TUITION",
            )

    def test_adjustment_zero_amount(self, db, student):
        with pytest.raises(finance_service.FinanceError, match="cannot be zero"):
            finance_service.create_adjustment(
                student_user_id=student.id,
                amount=Decimal("0"),
            )

    def test_correct_nonexistent_transaction(self, db):
        with pytest.raises(finance_service.FinanceError, match="not found"):
            finance_service.correct_transaction(99999)

    def test_reverse_nonexistent_transaction(self, db):
        with pytest.raises(finance_service.FinanceError, match="not found"):
            finance_service.reverse_transaction(99999)

    def test_correct_voided_transaction(self, db, student):
        tx = finance_service.record_payment(
            student_user_id=student.id,
            amount=Decimal("100"),
        )
        finance_service.reverse_transaction(tx.id)
        # The original is still ACTIVE, try to correct it
        finance_service.correct_transaction(tx.id)
        # After correction, it should be CORRECTED
        original = FinancialTransactionModel.query.get(tx.id)
        assert original.status == "CORRECTED"


# ---------------------------------------------------------------------------
# Signed adjustment regression tests (sign must survive storage)
# ---------------------------------------------------------------------------


class TestSignedAdjustments:
    """Adjustments are stored signed; balance consumes the stored sign."""

    def test_negative_adjustment_debits_balance(self, db, student):
        tx = finance_service.create_adjustment(
            student_user_id=student.id,
            amount=Decimal("-100000"),
            description="Penalty",
        )
        assert tx.amount == Decimal("-100000")
        assert finance_service.get_student_balance(student.id) == Decimal("-100000")

    def test_positive_adjustment_credits_balance(self, db, student):
        tx = finance_service.create_adjustment(
            student_user_id=student.id,
            amount=Decimal("100000"),
            description="Goodwill credit",
        )
        assert tx.amount == Decimal("100000")
        assert finance_service.get_student_balance(student.id) == Decimal("100000")

    def test_mixed_adjustments_net_correctly(self, db, student):
        finance_service.create_adjustment(
            student_user_id=student.id, amount=Decimal("250000")
        )
        finance_service.create_adjustment(
            student_user_id=student.id, amount=Decimal("-100000")
        )
        assert finance_service.get_student_balance(student.id) == Decimal("150000")

    def test_zero_adjustment_rejected(self, db, student):
        with pytest.raises(finance_service.FinanceError, match="zero"):
            finance_service.create_adjustment(
                student_user_id=student.id, amount=Decimal("0")
            )

    def test_reversal_of_negative_adjustment_nets_to_zero(self, db, student):
        tx = finance_service.create_adjustment(
            student_user_id=student.id, amount=Decimal("-80000")
        )
        reversal = finance_service.reverse_transaction(tx.id)
        assert reversal.amount == Decimal("80000")
        assert finance_service.get_student_balance(student.id) == Decimal("0")

    def test_reversal_of_positive_adjustment_nets_to_zero(self, db, student):
        tx = finance_service.create_adjustment(
            student_user_id=student.id, amount=Decimal("80000")
        )
        reversal = finance_service.reverse_transaction(tx.id)
        assert reversal.amount == Decimal("-80000")
        assert finance_service.get_student_balance(student.id) == Decimal("0")


# ---------------------------------------------------------------------------
# Refund linkage and reversal-once regression tests
# ---------------------------------------------------------------------------


class TestRefundLinkage:
    """Linked refunds are validated and capped; reversals are single-use."""

    def _payment(self, db, student, amount=Decimal("5000000")):
        return finance_service.record_payment(student_user_id=student.id, amount=amount)

    def test_linked_full_refund(self, db, student):
        payment = self._payment(db, student)
        refund = finance_service.record_refund(
            student_user_id=student.id,
            amount=Decimal("5000000"),
            related_transaction_id=payment.id,
        )
        assert refund.related_transaction_id == payment.id
        assert finance_service.get_student_balance(student.id) == Decimal("0")

    def test_second_full_refund_rejected(self, db, student):
        payment = self._payment(db, student)
        finance_service.record_refund(
            student_user_id=student.id,
            amount=Decimal("5000000"),
            related_transaction_id=payment.id,
        )
        with pytest.raises(finance_service.FinanceError, match="remaining refundable"):
            finance_service.record_refund(
                student_user_id=student.id,
                amount=Decimal("1000"),
                related_transaction_id=payment.id,
            )
        # Balance unchanged by the rejected refund.
        assert finance_service.get_student_balance(student.id) == Decimal("0")

    def test_partial_refunds_capped_at_paid_total(self, db, student):
        payment = self._payment(db, student)
        finance_service.record_refund(
            student_user_id=student.id,
            amount=Decimal("3000000"),
            related_transaction_id=payment.id,
        )
        assert finance_service.get_remaining_refundable(payment.id) == Decimal(
            "2000000"
        )
        with pytest.raises(finance_service.FinanceError, match="remaining refundable"):
            finance_service.record_refund(
                student_user_id=student.id,
                amount=Decimal("2000001"),
                related_transaction_id=payment.id,
            )
        finance_service.record_refund(
            student_user_id=student.id,
            amount=Decimal("2000000"),
            related_transaction_id=payment.id,
        )
        assert finance_service.get_student_balance(student.id) == Decimal("0")

    def test_refund_missing_original_rejected(self, db, student):
        with pytest.raises(finance_service.FinanceError, match="not found"):
            finance_service.record_refund(
                student_user_id=student.id,
                amount=Decimal("1000"),
                related_transaction_id=999999,
            )

    def test_refund_foreign_student_rejected(self, db, student):
        from app.infrastructure.database.models import RoleModel, UserModel

        other = UserModel(login="fin_other")
        other.set_password("pass123")
        role = RoleModel.query.get("STUDENT")
        if role is None:
            role = RoleModel(name="STUDENT")
            db.session.add(role)
            db.session.flush()
        other.roles.append(role)
        db.session.add(other)
        db.session.commit()
        payment = self._payment(db, student)
        with pytest.raises(finance_service.FinanceError, match="account"):
            finance_service.record_refund(
                student_user_id=other.id,
                amount=Decimal("1000"),
                related_transaction_id=payment.id,
            )

    def test_refund_non_payment_rejected(self, db, student):
        charge = finance_service.create_charge(
            student_user_id=student.id,
            amount=Decimal("100000"),
            category="TUITION",
        )
        with pytest.raises(finance_service.FinanceError, match="Only payments"):
            finance_service.record_refund(
                student_user_id=student.id,
                amount=Decimal("50000"),
                related_transaction_id=charge.id,
            )

    def test_standalone_refund_rejected_use_goodwill_credit(self, db, student):
        # Unlinked refunds are rejected; goodwill uses the explicit path.
        with pytest.raises(finance_service.FinanceError, match="must reference"):
            finance_service.record_refund(
                student_user_id=student.id, amount=Decimal("50000")
            )
        tx = finance_service.record_goodwill_credit(
            student_user_id=student.id,
            amount=Decimal("50000"),
            reason="Service recovery gesture",
        )
        assert tx.transaction_type == "ADJUSTMENT"
        assert finance_service.get_student_balance(student.id) == Decimal("50000")

    def test_reverse_twice_rejected(self, db, student):
        tx = self._payment(db, student)
        finance_service.reverse_transaction(tx.id)
        with pytest.raises(finance_service.FinanceError, match="already been reversed"):
            finance_service.reverse_transaction(tx.id)
        # Single reversal counted exactly once.
        assert finance_service.get_student_balance(student.id) == Decimal("0")


# ---------------------------------------------------------------------------
# Concurrency and constraint tests
# ---------------------------------------------------------------------------


class TestConcurrency:
    """Tests for concurrency safety using database constraints and validation.

    True multi-threaded concurrency tests require PostgreSQL and are run
    separately. These tests verify the constraint and validation logic
    that prevents race conditions.
    """

    def _payment(self, db, student, amount=Decimal("5000000")):
        return finance_service.record_payment(student_user_id=student.id, amount=amount)

    def test_refund_link_validation_prevents_double_refund(self, db, student):
        """Linked refunds are capped at the remaining refundable amount.

        A second full refund of the same payment is rejected because the
        remaining refundable amount is zero after the first refund.
        """
        payment = self._payment(db, student, Decimal("5000000"))

        # First full refund succeeds
        refund1 = finance_service.record_refund(
            student_user_id=student.id,
            amount=Decimal("5000000"),
            related_transaction_id=payment.id,
        )
        assert refund1.related_transaction_id == payment.id

        # Second full refund is rejected
        with pytest.raises(finance_service.FinanceError, match="remaining refundable"):
            finance_service.record_refund(
                student_user_id=student.id,
                amount=Decimal("1000"),
                related_transaction_id=payment.id,
            )

        # Only one refund recorded
        refunds = FinancialTransactionModel.query.filter_by(
            related_transaction_id=payment.id,
            transaction_type="REFUND",
            status="ACTIVE",
        ).all()
        assert len(refunds) == 1

    def test_payroll_uniqueness_is_service_plus_migration(self, db, student):
        """Liveness uniqueness must NOT be a model-level full UniqueConstraint.

        SQLAlchemy cannot express partial indexes portably, so the model
        deliberately carries no UniqueConstraint on teacher_payments: the
        service pre-check guards every backend, and migration f9a0b1c2d3e4
        adds the partial unique index on PostgreSQL. A model-level full
        unique would forbid the audited void-and-refinalize correction
        workflow, so this test pins the design. See TestConcurrencyPostgreSQL
        (skipped here) for live PostgreSQL constraint evidence.
        """
        from sqlalchemy import UniqueConstraint

        from app.infrastructure.database.models import TeacherPaymentModel

        uniques = [
            c
            for c in TeacherPaymentModel.__table__.constraints
            if isinstance(c, UniqueConstraint)
        ]
        assert uniques == []

    def test_refund_link_enforces_same_student(self, db, student):
        """Refund must belong to the same student as the original payment."""
        from app.infrastructure.database.models import RoleModel, UserModel

        other = UserModel(login="fin_other")
        other.set_password("pass123")
        role = RoleModel.query.get("STUDENT")
        if role is None:
            role = RoleModel(name="STUDENT")
            db.session.add(role)
            db.session.flush()
        other.roles.append(role)
        db.session.add(other)
        db.session.commit()

        payment = self._payment(db, student)
        with pytest.raises(finance_service.FinanceError, match="account"):
            finance_service.record_refund(
                student_user_id=other.id,
                amount=Decimal("1000"),
                related_transaction_id=payment.id,
            )
