"""Tests for the demo temprana academy generator (app.demo_seed_full).

The database guard itself is tested as pure refusal logic. Seed-logic
tests run against the isolated in-memory SQLite test database with the
guard explicitly bypassed (documented below); the guard's production
refusal is covered by the tests above plus live verification documented
in docs/DEMO.md. No test touches a live database.
"""

import pytest

from app.demo_seed_full import (
    _RESET_TABLES,
    DEMO_DATABASE_NAME,
    DEMO_PASSWORD,
    NotDemoEnvironmentError,
    assert_demo_environment,
    seed_demo_full,
)


def test_guard_requires_demo_mode(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv(
        "DATABASE_URL",
        f"postgresql+psycopg2://u:p@127.0.0.1:5432/{DEMO_DATABASE_NAME}",
    )
    with pytest.raises(NotDemoEnvironmentError):
        assert_demo_environment()


def test_guard_rejects_non_demo_url(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg2://u:p@127.0.0.1:5432/school_manager",
    )
    with pytest.raises(NotDemoEnvironmentError):
        assert_demo_environment()


def test_guard_rejects_missing_url(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(NotDemoEnvironmentError):
        assert_demo_environment()


def test_guard_rejects_wrong_live_database(monkeypatch, app):
    """Even with a demo-looking URL, a non-demo live connection refuses."""
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv(
        "DATABASE_URL",
        f"postgresql+psycopg2://u:p@127.0.0.1:5432/{DEMO_DATABASE_NAME}",
    )

    class _Scalar:
        def scalar(self):
            return "school_manager"

    from app.extensions import db as _db

    with app.app_context():
        monkeypatch.setattr(_db.session, "execute", lambda *args, **kwargs: _Scalar())
        with pytest.raises(NotDemoEnvironmentError):
            assert_demo_environment()


def test_reset_allowlist_never_touches_migrations():
    assert "alembic_version" not in _RESET_TABLES
    for required in (
        "users",
        "enrollments",
        "sessions",
        "attendances",
        "assessments",
        "financial_transactions",
        "teacher_payments",
        "audit_logs",
    ):
        assert required in _RESET_TABLES


def _seed_sqlite(db, monkeypatch):
    """Run the full seeder on the throwaway SQLite test DB.

    The environment guard is bypassed here on purpose: the target is the
    isolated in-memory test database (see conftest), never a live one.
    Guard behavior itself is tested above.
    """
    monkeypatch.setattr(
        "app.demo_seed_full.assert_demo_environment",
        lambda: "test-sqlite",
    )
    return seed_demo_full(db)


def test_seed_covers_expected_academy(db, monkeypatch):
    stats = _seed_sqlite(db, monkeypatch)
    assert (
        stats["users"] == 1 + 4 + 12 + 100 + 8
    )  # admin+staff, teachers, students, parents
    assert stats["courses"] == 10
    assert stats["classes"] == 40
    assert stats["enrollments"] >= 200
    assert stats["sessions"] > 400
    assert stats["attendances"] > 500
    assert stats["assessments"] >= 20
    assert stats["results"] > 0
    assert stats["transactions"] > 100
    assert stats["contracts"] >= 12
    assert stats["payments"] >= 18


def test_seed_is_idempotent(db, monkeypatch):
    first = _seed_sqlite(db, monkeypatch)
    second = _seed_sqlite(db, monkeypatch)
    assert first == second


def test_seed_relationship_integrity(db, monkeypatch):
    _seed_sqlite(db, monkeypatch)
    from app.infrastructure.database.models import (
        AcademyClassModel,
        AssessmentResultModel,
        AttendanceModel,
        EnrollmentModel,
        SessionModel,
        UserModel,
    )

    user_ids = {u.id for u in UserModel.query.all()}
    class_ids = {c.id for c in AcademyClassModel.query.all()}
    approved = {e.id for e in EnrollmentModel.query.filter_by(status="APPROVED").all()}
    session_class = {s.id: s.class_id for s in SessionModel.query.all()}
    enrollment_class = {e.id: e.class_id for e in EnrollmentModel.query.all()}

    for e in EnrollmentModel.query.all():
        assert e.student_user_id in user_ids
        assert e.class_id in class_ids
    for a in AttendanceModel.query.all():
        assert a.enrollment_id in approved
        assert enrollment_class[a.enrollment_id] == session_class[a.session_id]
    for r in AssessmentResultModel.query.all():
        assert r.enrollment_id in approved


def test_seed_finance_reconciles(db, monkeypatch):
    _seed_sqlite(db, monkeypatch)
    from decimal import Decimal

    from app.application.finance.finance_service import get_student_balance
    from app.infrastructure.database.models import (
        FinancialTransactionModel,
        UserModel,
    )

    students = (
        UserModel.query.filter(UserModel.roles.any(name="STUDENT")).limit(25).all()
    )
    assert students
    for s in students:
        rows = FinancialTransactionModel.query.filter_by(
            student_user_id=s.id, status="ACTIVE"
        ).all()
        expected = Decimal("0")
        for r in rows:
            if r.transaction_type in ("PAYMENT", "DISCOUNT", "REVERSAL", "ADJUSTMENT"):
                expected += Decimal(str(r.amount))
            else:
                expected -= Decimal(str(r.amount))
        assert Decimal(str(get_student_balance(s.id))) == expected


def test_demo_credentials_use_real_hashing(db, monkeypatch):
    _seed_sqlite(db, monkeypatch)
    from app.infrastructure.database.models import UserModel

    for login in ("admin", "staff1", "teacher1", "student1", "parent1"):
        user = UserModel.query.filter_by(login=login).first()
        assert user is not None
        assert user.password_hash != DEMO_PASSWORD
        assert user.check_password(DEMO_PASSWORD)
        assert user.must_change_password is False
        assert user.is_active_user is True


def test_demo_seed_cli_refuses_non_demo(runner, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    result = runner.invoke(args=["demo-seed"])
    assert result.exit_code != 0
    assert "Refusing" in result.output


def test_demo_reset_cli_requires_confirmation(runner, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv(
        "DATABASE_URL",
        f"postgresql+psycopg2://u:p@127.0.0.1:5432/{DEMO_DATABASE_NAME}",
    )
    result = runner.invoke(args=["demo-reset"])
    assert result.exit_code != 0
    assert "--yes" in result.output
