"""PostgreSQL concurrency tests — real threads, real transactions.

Run ONLY explicitly (never part of the default suite):

    TEST_DATABASE_URL='postgresql+psycopg2:///sm_conc_test?host=/var/run/postgresql' \\
    PG_CONCURRENCY_TESTS=1 \\
        python -m pytest tests/test_pg_concurrency.py -q

Requires a PostgreSQL server with a scratch database the current OS user
can create/drop tables in (peer auth). Each test rebuilds the schema, uses
barrier-synchronised threads with separate app contexts (hence separate
sessions from the same engine pool), and asserts final ledger invariants —
not merely HTTP codes.

What these tests prove: advisory locks + constraints serialize the
validate-then-insert units, so concurrent financial operations cannot
double-apply. What they do not prove: behavior under hundreds of
contending clients or failover (needs load testing).
"""

from __future__ import annotations

import os
import threading
from datetime import date, time
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("PG_CONCURRENCY_TESTS") != "1",
    reason="PostgreSQL concurrency tests run only when PG_CONCURRENCY_TESTS=1 "
    "with TEST_DATABASE_URL pointing at a scratch PostgreSQL database.",
)

from app import create_app  # noqa: E402
from app.extensions import db as _db  # noqa: E402


@pytest.fixture(scope="module")
def pg_app():
    app = create_app("testing")
    dialect = app.config["SQLALCHEMY_DATABASE_URI"]
    assert dialect.startswith("postgres"), (
        f"Refusing to run concurrency tests on non-PostgreSQL backend: {dialect}"
    )
    return app


@pytest.fixture()
def pg_db(pg_app):
    with pg_app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


def _run_pair(fn):
    """Run fn() in two barrier-synced threads; return (results, errors)."""
    barrier = threading.Barrier(2)
    outcomes = []

    def worker():
        barrier.wait(timeout=30)
        try:
            fn()
            outcomes.append("ok")
        except Exception as exc:  # noqa: BLE001 - collected for assertions
            outcomes.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    assert all(not t.is_alive() for t in threads), "worker thread hung"
    return outcomes


def _make_student(db, login="conc_student", national_id="1111111111"):
    from app.infrastructure.database.models import (
        RoleModel,
        StudentProfileModel,
        UserModel,
    )

    user = UserModel(login=login)
    user.set_password("pass123")
    role = RoleModel.query.get("STUDENT")
    if role is None:
        role = RoleModel(name="STUDENT")
        db.session.add(role)
        db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.flush()
    db.session.add(
        StudentProfileModel(
            user_id=user.id,
            first_name="Conc",
            last_name="Student",
            national_id=national_id,
            mobile_phone="09120000001",
            birth_date=date(2000, 1, 1),
            gender="MALE",
        )
    )
    db.session.commit()
    return user


def _make_teacher_setup(db, login="conc_teacher"):
    from app.infrastructure.database.models import (
        AcademyClassModel,
        CourseModel,
        RoleModel,
        SessionModel,
        TeacherContractModel,
        TeacherProfileModel,
        UserModel,
    )

    teacher = UserModel(login=login)
    teacher.set_password("pass123")
    role = RoleModel.query.get("TEACHER")
    if role is None:
        role = RoleModel(name="TEACHER")
        db.session.add(role)
        db.session.flush()
    teacher.roles.append(role)
    db.session.add(teacher)
    db.session.flush()
    db.session.add(
        TeacherProfileModel(
            user_id=teacher.id,
            first_name="Conc",
            last_name="Teacher",
            national_id="2222222222",
            mobile_phone="09120000002",
        )
    )
    course = CourseModel(title="Conc", description="d", num_sessions=4)
    db.session.add(course)
    db.session.flush()
    cls = AcademyClassModel(
        course_id=course.id,
        title="Conc Class",
        start_date=date(2026, 1, 1),
        capacity=10,
        num_sessions=4,
        status="ACTIVE",
        teacher_user_id=teacher.id,
    )
    db.session.add(cls)
    db.session.flush()
    db.session.add(
        TeacherContractModel(
            teacher_user_id=teacher.id,
            class_id=cls.id,
            payment_type="PER_SESSION",
            rate=Decimal("500000"),
            is_active=True,
        )
    )
    db.session.add(
        SessionModel(
            class_id=cls.id,
            session_number=1,
            scheduled_date=date(2026, 3, 1),
            start_time=time(10, 0),
            end_time=time(12, 0),
            status="COMPLETED",
            title="S1",
        )
    )
    db.session.commit()
    return teacher


class TestConcurrentRefundsPG:
    def test_two_full_refunds_single_winner(self, pg_app, pg_db):
        """Two simultaneous full refunds of one payment: exactly one wins."""
        from app.application.finance import finance_service
        from app.infrastructure.database.models import FinancialTransactionModel

        student = _make_student(pg_db)
        payment = finance_service.record_payment(
            student_user_id=student.id, amount=Decimal("5000000")
        )
        payment_id, student_id = payment.id, student.id

        def attempt():
            with pg_app.app_context():
                finance_service.record_refund(
                    student_user_id=student_id,
                    amount=Decimal("5000000"),
                    related_transaction_id=payment_id,
                )

        outcomes = _run_pair(attempt)
        assert outcomes.count("ok") == 1, outcomes
        failures = [o for o in outcomes if o != "ok"]
        assert len(failures) == 1
        assert "refundable" in str(failures[0]).lower()

        with pg_app.app_context():
            refunds = FinancialTransactionModel.query.filter_by(
                related_transaction_id=payment_id,
                transaction_type="REFUND",
                status="ACTIVE",
            ).all()
            assert len(refunds) == 1
            balance = finance_service.get_student_balance(student_id)
            assert balance == Decimal("0")


class TestConcurrentFinalizePG:
    def test_two_finalizes_single_row(self, pg_app, pg_db):
        """Two simultaneous finalizations for one teacher+period: one row."""
        from app.application.payroll import services as payroll_services
        from app.application.payroll.services import PayrollError
        from app.infrastructure.database.models import TeacherPaymentModel

        teacher = _make_teacher_setup(pg_db)
        teacher_id = teacher.id

        def attempt():
            with pg_app.app_context():
                payroll_services.finalize_payroll(
                    teacher_user_id=teacher_id,
                    period_start=date(2026, 3, 1),
                    period_end=date(2026, 3, 31),
                )

        outcomes = _run_pair(attempt)
        assert outcomes.count("ok") == 1, outcomes
        failures = [o for o in outcomes if o != "ok"]
        assert len(failures) == 1
        assert isinstance(failures[0], PayrollError)

        with pg_app.app_context():
            rows = TeacherPaymentModel.query.filter_by(
                teacher_user_id=teacher_id,
                period_start=date(2026, 3, 1),
                period_end=date(2026, 3, 31),
            ).all()
            assert len(rows) == 1


class TestConcurrentCallbacksPG:
    def _pending_tx(self, db, student_id, ref, amount=Decimal("100000")):
        from app.infrastructure.database.models import FinancialTransactionModel

        tx = FinancialTransactionModel(
            student_user_id=student_id,
            amount=amount,
            transaction_type="PAYMENT",
            category="OTHER",
            description="Test",
            reference_number=ref,
            payment_method="ONLINE",
            status="PENDING",
        )
        db.session.add(tx)
        db.session.commit()
        return tx.id

    def test_two_ok_callbacks_single_credit(self, pg_app, pg_db):
        """Two simultaneous successful callbacks: one credit, both succeed."""
        from app.application.finance import finance_service
        from app.application.finance.payment_service import process_payment_callback
        from app.infrastructure.database.models import FinancialTransactionModel
        from app.infrastructure.payment.gateway import PaymentVerificationResult

        student = _make_student(pg_db)
        self._pending_tx(pg_db, student.id, "S0000000000000000000000000000CCOK01")
        student_id = student.id

        gateway = MagicMock()
        gateway.verify_payment.return_value = PaymentVerificationResult(
            success=True, ref_id="REFCCOK01"
        )
        with patch(
            "app.application.finance.payment_service._get_gateway",
            return_value=gateway,
        ):

            def attempt():
                with pg_app.app_context():
                    process_payment_callback(
                        authority="S0000000000000000000000000000CCOK01",
                        amount=Decimal("100000"),
                        callback_status="OK",
                    )

            outcomes = _run_pair(attempt)
            assert outcomes.count("ok") == 2, outcomes

        with pg_app.app_context():
            rows = FinancialTransactionModel.query.filter_by(
                reference_number="S0000000000000000000000000000CCOK01"
            ).all()
            assert len(rows) == 1
            assert rows[0].status == "ACTIVE"
            balance = finance_service.get_student_balance(student_id)
            assert balance == Decimal("100000")

    def test_ok_vs_nok_race_never_loses_money(self, pg_app, pg_db):
        """A success racing a failure flag ends ACTIVE with a single credit
        when the provider confirms payment (ground truth wins)."""
        from app.application.finance import finance_service
        from app.application.finance.payment_service import process_payment_callback
        from app.infrastructure.database.models import FinancialTransactionModel
        from app.infrastructure.payment.gateway import PaymentVerificationResult

        student = _make_student(pg_db, login="conc_student2", national_id="3333333333")
        self._pending_tx(pg_db, student.id, "S0000000000000000000000000000RACE01")
        student_id = student.id

        gateway = MagicMock()
        gateway.verify_payment.return_value = PaymentVerificationResult(
            success=True, ref_id="REFRACE01"
        )
        with patch(
            "app.application.finance.payment_service._get_gateway",
            return_value=gateway,
        ):

            def attempt_ok():
                with pg_app.app_context():
                    process_payment_callback(
                        authority="S0000000000000000000000000000RACE01",
                        amount=Decimal("100000"),
                        callback_status="OK",
                    )

            def attempt_nok():
                with pg_app.app_context():
                    process_payment_callback(
                        authority="S0000000000000000000000000000RACE01",
                        amount=Decimal("100000"),
                        callback_status="NOK",
                    )

            barrier = threading.Barrier(2)
            outcomes = []

            def w1():
                barrier.wait(timeout=30)
                try:
                    attempt_ok()
                    outcomes.append("ok")
                except Exception as exc:  # noqa: BLE001
                    outcomes.append(exc)

            def w2():
                barrier.wait(timeout=30)
                try:
                    attempt_nok()
                    outcomes.append("ok")
                except Exception as exc:  # noqa: BLE001
                    outcomes.append(exc)

            threads = [threading.Thread(target=w1), threading.Thread(target=w2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=120)

            assert outcomes.count("ok") == 2, outcomes

        with pg_app.app_context():
            rows = FinancialTransactionModel.query.filter_by(
                reference_number="S0000000000000000000000000000RACE01"
            ).all()
            assert len(rows) == 1
            assert rows[0].status == "ACTIVE"
            assert finance_service.get_student_balance(student_id) == Decimal("100000")

    def test_ok_vs_definitive_fail_race_stays_consistent(self, pg_app, pg_db):
        """Success racing a definitive provider failure: single row, balance
        is either the full credit or zero — never double, never partial."""
        from app.application.finance import finance_service
        from app.application.finance.payment_service import process_payment_callback
        from app.infrastructure.database.models import FinancialTransactionModel
        from app.infrastructure.payment.gateway import PaymentVerificationResult

        student = _make_student(pg_db, login="conc_student3", national_id="4444444444")
        self._pending_tx(pg_db, student.id, "S0000000000000000000000000000RACE02")
        student_id = student.id

        gateway = MagicMock()
        gateway.verify_payment.return_value = PaymentVerificationResult(
            success=False, error="cancelled", error_code=-22
        )
        with patch(
            "app.application.finance.payment_service._get_gateway",
            return_value=gateway,
        ):

            def attempt():
                with pg_app.app_context():
                    process_payment_callback(
                        authority="S0000000000000000000000000000RACE02",
                        amount=Decimal("100000"),
                        callback_status="OK",
                    )

            outcomes = _run_pair(attempt)
            assert outcomes.count("ok") == 2, outcomes

        with pg_app.app_context():
            rows = FinancialTransactionModel.query.filter_by(
                reference_number="S0000000000000000000000000000RACE02"
            ).all()
            assert len(rows) == 1
            assert rows[0].status == "FAILED"
            assert finance_service.get_student_balance(student_id) == Decimal("0")
