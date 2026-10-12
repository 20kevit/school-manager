"""Tests for Phase 24 — Teacher Salaries & Payroll Management."""

from datetime import date, time
from decimal import Decimal

import pytest

from app.application.payroll.services import (
    PayrollError,
    calculate_teacher_payroll,
    create_contract,
    delete_contract,
    finalize_payroll,
    get_contract,
    list_contracts,
    list_payments,
    list_teachers_with_payroll_summary,
    mark_payment_paid,
    update_contract,
)
from app.infrastructure.database.models import (
    AcademyClassModel,
    CourseModel,
    FinancialTransactionModel,
    SessionModel,
    StudentProfileModel,
    TeacherContractModel,
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
def academy_class(db, course, teacher_user):
    cls = AcademyClassModel(
        course_id=course.id,
        title="کلاس پایتون",
        start_date=date(2026, 1, 1),
        capacity=30,
        tuition=Decimal("5000000"),
        num_sessions=10,
        status="ACTIVE",
        teacher_user_id=teacher_user.id,
    )
    db.session.add(cls)
    db.session.commit()
    return cls


@pytest.fixture
def academy_class_2(db, course, teacher_user):
    cls = AcademyClassModel(
        course_id=course.id,
        title="کلاس جاوا",
        start_date=date(2026, 1, 1),
        capacity=25,
        tuition=Decimal("6000000"),
        num_sessions=10,
        status="ACTIVE",
        teacher_user_id=teacher_user.id,
    )
    db.session.add(cls)
    db.session.commit()
    return cls


@pytest.fixture
def student(db):
    user = UserModel(login="pay_student")
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
        national_id="9999999999",
        mobile_phone="09129999999",
        birth_date=date(2000, 1, 15),
        gender="MALE",
    )
    db.session.add(profile)
    db.session.commit()
    return user


@pytest.fixture
def student_2(db):
    user = UserModel(login="pay_student2")
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
        national_id="8888888888",
        mobile_phone="09128888888",
        birth_date=date(2001, 5, 20),
        gender="FEMALE",
    )
    db.session.add(profile)
    db.session.commit()
    return user


@pytest.fixture
def completed_session(db, academy_class):
    session = SessionModel(
        class_id=academy_class.id,
        session_number=1,
        scheduled_date=date(2026, 3, 1),
        start_time=time(10, 0),
        end_time=time(12, 0),
        status="COMPLETED",
    )
    db.session.add(session)
    db.session.commit()
    return session


@pytest.fixture
def completed_session_2(db, academy_class):
    session = SessionModel(
        class_id=academy_class.id,
        session_number=2,
        scheduled_date=date(2026, 3, 5),
        start_time=time(10, 0),
        end_time=time(12, 0),
        status="COMPLETED",
    )
    db.session.add(session)
    db.session.commit()
    return session


@pytest.fixture
def scheduled_session(db, academy_class):
    session = SessionModel(
        class_id=academy_class.id,
        session_number=3,
        scheduled_date=date(2026, 3, 8),
        start_time=time(10, 0),
        end_time=time(12, 0),
        status="SCHEDULED",
    )
    db.session.add(session)
    db.session.commit()
    return session


@pytest.fixture
def per_session_contract(db, teacher_user, academy_class):
    contract = TeacherContractModel(
        teacher_user_id=teacher_user.id,
        class_id=academy_class.id,
        payment_type="PER_SESSION",
        rate=Decimal("500000"),
        is_active=True,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    db.session.add(contract)
    db.session.commit()
    return contract


@pytest.fixture
def percentage_contract(db, teacher_user, academy_class):
    contract = TeacherContractModel(
        teacher_user_id=teacher_user.id,
        class_id=academy_class.id,
        payment_type="PERCENTAGE_OF_REVENUE",
        rate=Decimal("20"),
        is_active=True,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    db.session.add(contract)
    db.session.commit()
    return contract


@pytest.fixture
def generic_contract(db, teacher_user):
    contract = TeacherContractModel(
        teacher_user_id=teacher_user.id,
        class_id=None,
        payment_type="PER_SESSION",
        rate=Decimal("400000"),
        is_active=True,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    db.session.add(contract)
    db.session.commit()
    return contract


# ---------------------------------------------------------------------------
# Contract CRUD Tests
# ---------------------------------------------------------------------------


class TestContractCRUD:
    """Tests for Teacher Contract CRUD operations."""

    def test_create_per_session_contract(self, db, teacher_user, academy_class):
        contract = create_contract(
            teacher_user_id=teacher_user.id,
            class_id=academy_class.id,
            payment_type="PER_SESSION",
            rate=Decimal("500000"),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        assert contract.id is not None
        assert contract.payment_type == "PER_SESSION"
        assert contract.rate == Decimal("500000")
        assert contract.is_active is True

    def test_create_percentage_contract(self, db, teacher_user, academy_class):
        contract = create_contract(
            teacher_user_id=teacher_user.id,
            class_id=academy_class.id,
            payment_type="PERCENTAGE_OF_REVENUE",
            rate=Decimal("20"),
        )
        assert contract.id is not None
        assert contract.payment_type == "PERCENTAGE_OF_REVENUE"
        assert contract.rate == Decimal("20")

    def test_create_generic_contract_no_class(self, db, teacher_user):
        contract = create_contract(
            teacher_user_id=teacher_user.id,
            class_id=None,
            payment_type="PER_SESSION",
            rate=Decimal("300000"),
        )
        assert contract.id is not None
        assert contract.class_id is None

    def test_create_contract_invalid_rate(self, db, teacher_user, academy_class):
        with pytest.raises(PayrollError, match="نرخ پرداخت باید مثبت باشد"):
            create_contract(
                teacher_user_id=teacher_user.id,
                class_id=academy_class.id,
                payment_type="PER_SESSION",
                rate=Decimal("-100"),
            )

    def test_create_contract_zero_rate(self, db, teacher_user, academy_class):
        with pytest.raises(PayrollError, match="نرخ پرداخت باید مثبت باشد"):
            create_contract(
                teacher_user_id=teacher_user.id,
                class_id=academy_class.id,
                payment_type="PER_SESSION",
                rate=Decimal("0"),
            )

    def test_create_contract_invalid_percentage(self, db, teacher_user, academy_class):
        with pytest.raises(PayrollError, match="درصد درآمد باید بین ۰ تا ۱۰۰ باشد"):
            create_contract(
                teacher_user_id=teacher_user.id,
                class_id=academy_class.id,
                payment_type="PERCENTAGE_OF_REVENUE",
                rate=Decimal("150"),
            )

    def test_create_contract_invalid_type(self, db, teacher_user, academy_class):
        with pytest.raises(PayrollError, match="نوع پرداخت نامعتبر است"):
            create_contract(
                teacher_user_id=teacher_user.id,
                class_id=academy_class.id,
                payment_type="HOURLY",
                rate=Decimal("100"),
            )

    def test_create_contract_nonexistent_teacher(self, db):
        with pytest.raises(PayrollError, match="معلم یافت نشد"):
            create_contract(
                teacher_user_id=99999,
                class_id=None,
                payment_type="PER_SESSION",
                rate=Decimal("100"),
            )

    def test_create_contract_nonexistent_class(self, db, teacher_user):
        with pytest.raises(PayrollError, match="کلاس یافت نشد"):
            create_contract(
                teacher_user_id=teacher_user.id,
                class_id=99999,
                payment_type="PER_SESSION",
                rate=Decimal("100"),
            )

    def test_update_contract(self, db, per_session_contract):
        updated = update_contract(
            per_session_contract,
            rate=Decimal("600000"),
        )
        assert updated.rate == Decimal("600000")
        assert updated.payment_type == "PER_SESSION"

    def test_update_contract_change_type(self, db, per_session_contract):
        updated = update_contract(
            per_session_contract,
            payment_type="PERCENTAGE_OF_REVENUE",
            rate=Decimal("25"),
        )
        assert updated.payment_type == "PERCENTAGE_OF_REVENUE"
        assert updated.rate == Decimal("25")

    def test_update_contract_deactivate(self, db, per_session_contract):
        updated = update_contract(per_session_contract, is_active=False)
        assert updated.is_active is False

    def test_delete_contract_soft(self, db, per_session_contract):
        delete_contract(per_session_contract)
        assert per_session_contract.is_active is False

    def test_list_contracts_active_only(self, db, per_session_contract, teacher_user):
        delete_contract(per_session_contract)
        active = list_conacts_filter(teacher_user.id, active_only=True)
        assert len(active) == 0

    def test_list_contracts_includes_inactive(
        self, db, per_session_contract, teacher_user
    ):
        delete_contract(per_session_contract)
        all_contracts = list_conacts_filter(teacher_user.id, active_only=False)
        assert len(all_contracts) == 1

    def test_get_contract(self, db, per_session_contract):
        found = get_contract(per_session_contract.id)
        assert found is not None
        assert found.id == per_session_contract.id

    def test_get_contract_not_found(self, db):
        found = get_contract(99999)
        assert found is None


def list_conacts_filter(teacher_id, active_only=True):
    """Helper to test list_contracts."""

    return list_contracts(teacher_user_id=teacher_id, active_only=active_only)


# ---------------------------------------------------------------------------
# Payroll Calculation Tests
# ---------------------------------------------------------------------------


class TestPayrollCalculation:
    """Tests for payroll calculation logic."""

    def test_per_session_no_sessions(self, db, teacher_user, per_session_contract):
        summary = calculate_teacher_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        assert summary.total_sessions == 0
        assert summary.gross_amount == Decimal("0")

    def test_per_session_with_completed_sessions(
        self,
        db,
        teacher_user,
        academy_class,
        per_session_contract,
        completed_session,
        completed_session_2,
    ):
        summary = calculate_teacher_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        assert summary.total_sessions == 2
        assert summary.gross_amount == Decimal("1000000")  # 2 * 500000
        assert len(summary.breakdown_per_class) == 1
        assert summary.breakdown_per_class[0].session_count == 2
        assert summary.breakdown_per_class[0].amount == Decimal("1000000")

    def test_scheduled_sessions_not_counted(
        self,
        db,
        teacher_user,
        per_session_contract,
        completed_session,
        scheduled_session,
    ):
        summary = calculate_teacher_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        assert summary.total_sessions == 1  # Only completed

    def test_percentage_no_revenue(
        self, db, teacher_user, academy_class, percentage_contract, completed_session
    ):
        summary = calculate_teacher_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        assert summary.total_sessions == 1
        assert summary.gross_amount == Decimal("0")  # No collected revenue

    def test_percentage_with_revenue(
        self,
        db,
        teacher_user,
        academy_class,
        student,
        percentage_contract,
        completed_session,
    ):
        from datetime import datetime

        # Simulate collected tuition payment with explicit created_at in the period
        payment = FinancialTransactionModel(
            student_user_id=student.id,
            amount=Decimal("5000000"),
            transaction_type="PAYMENT",
            category="TUITION",
            class_id=academy_class.id,
            status="ACTIVE",
            created_at=datetime(2026, 3, 10, 12, 0),
        )
        db.session.add(payment)
        db.session.commit()

        summary = calculate_teacher_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        assert summary.total_sessions == 1
        # 5000000 * 20% = 1000000
        assert summary.gross_amount == Decimal("1000000")
        assert summary.breakdown_per_class[0].collected_revenue == Decimal("5000000")

    def test_percentage_counts_ordinary_channel_payments(
        self,
        db,
        teacher_user,
        academy_class,
        student,
        percentage_contract,
        completed_session,
    ):
        """Payments recorded via record_payment (category OTHER) must count.

        Regression: the revenue query used to require category TUITION while
        every real intake path writes OTHER, yielding zero payroll.
        """
        from datetime import datetime

        from app.application.finance import finance_service

        for amount in (Decimal("5000000"), Decimal("3000000")):
            tx = finance_service.record_payment(
                student_user_id=student.id,
                amount=amount,
                payment_method="CASH",
                class_id=academy_class.id,
            )
            assert tx.category == "OTHER"
            tx.created_at = datetime(2026, 3, 10, 12, 0)
        db.session.commit()

        summary = calculate_teacher_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        assert summary.breakdown_per_class[0].collected_revenue == Decimal("8000000")
        # 8000000 * 20% = 1600000
        assert summary.gross_amount == Decimal("1600000")

    def test_percentage_ignores_unlinked_and_unsettled_payments(
        self,
        db,
        teacher_user,
        academy_class,
        student,
        percentage_contract,
        completed_session,
    ):
        """class_id NULL, PENDING, and FAILED payments must not count."""
        from datetime import datetime

        from app.application.finance import finance_service
        from app.infrastructure.database.models import FinancialTransactionModel

        tx = finance_service.record_payment(
            student_user_id=student.id, amount=Decimal("9000000")
        )
        tx.created_at = datetime(2026, 3, 10, 12, 0)
        for status in ("PENDING", "FAILED"):
            db.session.add(
                FinancialTransactionModel(
                    student_user_id=student.id,
                    amount=Decimal("7000000"),
                    transaction_type="PAYMENT",
                    category="OTHER",
                    class_id=academy_class.id,
                    payment_method="ONLINE",
                    status=status,
                    created_at=datetime(2026, 3, 10, 12, 0),
                )
            )
        db.session.commit()

        summary = calculate_teacher_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        assert summary.breakdown_per_class[0].collected_revenue == Decimal("0")
        assert summary.gross_amount == Decimal("0")

    def test_generic_contract_fallback(
        self, db, teacher_user, academy_class, generic_contract, completed_session
    ):
        summary = calculate_teacher_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        assert summary.total_sessions == 1
        assert summary.gross_amount == Decimal("400000")  # Generic contract rate

    def test_class_specific_over_generic(
        self, db, teacher_user, academy_class, generic_contract, completed_session
    ):
        # Create class-specific contract with higher rate
        specific = TeacherContractModel(
            teacher_user_id=teacher_user.id,
            class_id=academy_class.id,
            payment_type="PER_SESSION",
            rate=Decimal("700000"),
            is_active=True,
        )
        db.session.add(specific)
        db.session.commit()

        summary = calculate_teacher_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        # Should use class-specific rate (700000), not generic (400000)
        assert summary.gross_amount == Decimal("700000")

    def test_date_range_filtering(self, db, teacher_user, per_session_contract):
        # Session outside the range
        session = SessionModel(
            class_id=per_session_contract.class_id,
            session_number=1,
            scheduled_date=date(2026, 4, 5),
            start_time=time(10, 0),
            end_time=time(12, 0),
            status="COMPLETED",
        )
        db.session.add(session)
        db.session.commit()

        # Query for March only
        summary = calculate_teacher_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        assert summary.total_sessions == 0

    def test_multiple_classes(self, db, teacher_user, academy_class, academy_class_2):
        # Contract for class 1
        contract1 = TeacherContractModel(
            teacher_user_id=teacher_user.id,
            class_id=academy_class.id,
            payment_type="PER_SESSION",
            rate=Decimal("500000"),
            is_active=True,
        )
        # Contract for class 2
        contract2 = TeacherContractModel(
            teacher_user_id=teacher_user.id,
            class_id=academy_class_2.id,
            payment_type="PER_SESSION",
            rate=Decimal("600000"),
            is_active=True,
        )
        db.session.add_all([contract1, contract2])
        db.session.flush()

        # Sessions for each class
        s1 = SessionModel(
            class_id=academy_class.id,
            session_number=1,
            scheduled_date=date(2026, 3, 1),
            start_time=time(10, 0),
            end_time=time(12, 0),
            status="COMPLETED",
        )
        s2 = SessionModel(
            class_id=academy_class_2.id,
            session_number=1,
            scheduled_date=date(2026, 3, 5),
            start_time=time(14, 0),
            end_time=time(16, 0),
            status="COMPLETED",
        )
        db.session.add_all([s1, s2])
        db.session.commit()

        summary = calculate_teacher_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        assert summary.total_sessions == 2
        assert summary.gross_amount == Decimal("1100000")  # 500000 + 600000
        assert len(summary.breakdown_per_class) == 2


# ---------------------------------------------------------------------------
# Payroll Finalization Tests
# ---------------------------------------------------------------------------


class TestPayrollFinalization:
    """Tests for payroll finalization and payment status."""

    def test_finalize_payroll(
        self, db, teacher_user, per_session_contract, completed_session
    ):
        payment = finalize_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        assert payment.id is not None
        assert payment.status == "PENDING"
        assert payment.gross_amount == Decimal("500000")
        assert payment.net_amount == Decimal("500000")

    def test_finalize_with_deductions(
        self, db, teacher_user, per_session_contract, completed_session
    ):
        payment = finalize_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
            deductions=Decimal("50000"),
        )
        assert payment.gross_amount == Decimal("500000")
        assert payment.deductions == Decimal("50000")
        assert payment.net_amount == Decimal("450000")

    def test_finalize_no_sessions_raises(self, db, teacher_user, per_session_contract):
        with pytest.raises(PayrollError, match="جلسه تکمیل شده‌ای"):
            finalize_payroll(
                teacher_user.id,
                date(2026, 3, 1),
                date(2026, 3, 31),
            )

    def test_finalize_duplicate_raises(
        self, db, teacher_user, per_session_contract, completed_session
    ):
        finalize_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        with pytest.raises(PayrollError, match="قرارداد پرداخت برای این دوره قبلاً"):
            finalize_payroll(
                teacher_user.id,
                date(2026, 3, 1),
                date(2026, 3, 31),
            )

    def test_finalize_negative_deductions_raises(
        self, db, teacher_user, per_session_contract, completed_session
    ):
        with pytest.raises(PayrollError, match="کسورات نمی‌تواند منفی"):
            finalize_payroll(
                teacher_user.id,
                date(2026, 3, 1),
                date(2026, 3, 31),
                deductions=Decimal("-100"),
            )

    def test_mark_payment_paid(
        self, db, teacher_user, per_session_contract, completed_session
    ):
        payment = finalize_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        paid = mark_payment_paid(payment)
        assert paid.status == "PAID"
        assert paid.paid_at is not None

    def test_mark_already_paid_raises(
        self, db, teacher_user, per_session_contract, completed_session
    ):
        payment = finalize_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        mark_payment_paid(payment)
        with pytest.raises(PayrollError, match="این پرداخت قبلاً پرداخت شده"):
            mark_payment_paid(payment)

    def test_list_payments(
        self, db, teacher_user, per_session_contract, completed_session
    ):
        finalize_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        payments = list_payments(teacher_user_id=teacher_user.id)
        assert len(payments) == 1

    def test_list_payments_by_status(
        self, db, teacher_user, per_session_contract, completed_session
    ):
        payment = finalize_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        pending = list_payments(status="PENDING")
        assert len(pending) == 1

        mark_payment_paid(payment)
        paid = list_payments(status="PAID")
        assert len(paid) == 1

    def test_list_teachers_with_summary(
        self, db, teacher_user, per_session_contract, completed_session
    ):
        results = list_teachers_with_payroll_summary(
            date(2026, 3, 1),
            date(2026, 3, 31),
        )
        assert len(results) >= 1
        teacher_result = next(r for r in results if r["teacher"].id == teacher_user.id)
        assert teacher_result["summary"].total_sessions == 1


# ---------------------------------------------------------------------------
# Admin UI Tests
# ---------------------------------------------------------------------------


class TestPayrollAdminUI:
    """Tests for admin payroll UI routes."""

    def test_contract_list_requires_admin(self, client, teacher_user):
        """Non-admin users cannot access contract list."""
        response = client.get("/admin/contracts")
        assert response.status_code in (302, 403)

    def test_contract_list_admin(self, client, admin_user, teacher_user):
        """Admin can access contract list."""
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
            follow_redirects=False,
        )
        response = client.get("/admin/contracts")
        assert response.status_code == 200

    def test_contract_create_form(self, client, admin_user, teacher_user):
        """Admin can access contract create form."""
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
            follow_redirects=False,
        )
        response = client.get("/admin/contracts/create")
        assert response.status_code == 200

    def test_contract_create_post(
        self, client, admin_user, teacher_user, academy_class
    ):
        """Admin can create a contract."""
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
            follow_redirects=False,
        )
        response = client.post(
            "/admin/contracts/create",
            data={
                "teacher_user_id": teacher_user.id,
                "class_id": academy_class.id,
                "payment_type": "PER_SESSION",
                "rate": "500000",
                "start_date": "1404/01/01",
                "end_date": "1404/12/29",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/admin/contracts" in response.headers["Location"]

    def test_payroll_page(self, client, admin_user, teacher_user):
        """Admin can access payroll page."""
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
            follow_redirects=False,
        )
        response = client.get("/admin/payroll?year=1405&month=6")
        assert response.status_code == 200

    def test_finalize_excessive_deductions_raises(
        self, db, teacher_user, per_session_contract, completed_session
    ):
        with pytest.raises(PayrollError, match="بیشتر"):
            finalize_payroll(
                teacher_user.id,
                date(2026, 3, 1),
                date(2026, 3, 31),
                deductions=Decimal("600000"),
            )

    def test_finalize_deductions_equal_gross_allowed(
        self, db, teacher_user, per_session_contract, completed_session
    ):
        payment = finalize_payroll(
            teacher_user.id,
            date(2026, 3, 1),
            date(2026, 3, 31),
            deductions=Decimal("500000"),
        )
        assert payment.net_amount == Decimal("0")

    def test_duplicate_payment_rejected_at_database_level(
        self, db, teacher_user
    ):
        """The unique constraint (not just the pre-check) blocks duplicates."""
        from sqlalchemy.exc import IntegrityError

        from app.infrastructure.database.models import TeacherPaymentModel

        db.session.add(
            TeacherPaymentModel(
                teacher_user_id=teacher_user.id,
                period_start=date(2026, 3, 1),
                period_end=date(2026, 3, 31),
                gross_amount=Decimal("500000"),
                deductions=Decimal("0"),
                net_amount=Decimal("500000"),
                status="PENDING",
            )
        )
        db.session.commit()
        db.session.add(
            TeacherPaymentModel(
                teacher_user_id=teacher_user.id,
                period_start=date(2026, 3, 1),
                period_end=date(2026, 3, 31),
                gross_amount=Decimal("500000"),
                deductions=Decimal("0"),
                net_amount=Decimal("500000"),
                status="PENDING",
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
