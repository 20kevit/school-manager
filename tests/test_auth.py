"""Tests for authentication."""

from datetime import date

import pytest

from app.application.auth.services import (
    AuthenticationError,
    authenticate,
    change_password,
    create_user,
)


class TestAuthentication:
    """Tests for authentication services."""

    def test_successful_login(self, client, sample_user):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/auth/dashboard" in response.headers["Location"]

    def test_invalid_credentials(self, client, sample_user):
        """Test login with invalid credentials."""
        response = client.post(
            "/auth/login",
            data={"login": "testuser", "password": "wrongpass"},
            follow_redirects=True,
        )
        assert response.status_code == 401

    def test_nonexistent_user(self, client, sample_user):
        """Test login with non-existent user."""
        response = client.post(
            "/auth/login",
            data={"login": "nonexistent", "password": "password"},
            follow_redirects=True,
        )
        assert response.status_code == 401

    def test_inactive_user_login(self, client, sample_user, db):
        """Test that inactive users cannot log in."""
        sample_user.is_active_user = False
        db.session.commit()

        response = client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
            follow_redirects=True,
        )
        assert response.status_code == 401

    def test_logout(self, client, sample_user):
        """Test logout."""
        # Login first
        client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
        )

        # Logout
        response = client.get("/auth/logout", follow_redirects=False)
        assert response.status_code == 302

        # Verify cannot access dashboard after logout
        response = client.get("/auth/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]

    def test_protected_route(self, client):
        """Test that protected routes require authentication."""
        response = client.get("/auth/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]

    def test_password_change(self, client, sample_user):
        """Test password change."""
        # Login
        client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
        )

        # Change password
        response = client.post(
            "/auth/change-password",
            data={
                "current_password": "testpass123",
                "new_password": "newpass123",
                "confirm_password": "newpass123",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

        # Verify new password works
        user = authenticate("testuser", "newpass123")
        assert user.login == "testuser"

    def test_password_change_wrong_current(self, client, sample_user):
        """Test password change with wrong current password."""
        # Login
        client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
        )

        # Try to change with wrong current password
        response = client.post(
            "/auth/change-password",
            data={
                "current_password": "wrongpass",
                "new_password": "newpass123",
                "confirm_password": "newpass123",
            },
            follow_redirects=True,
        )
        assert response.status_code == 400

    def test_password_change_mismatch(self, client, sample_user):
        """Test password change with mismatched new passwords."""
        # Login
        client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
        )

        # Try to change with mismatched passwords
        response = client.post(
            "/auth/change-password",
            data={
                "current_password": "testpass123",
                "new_password": "newpass123",
                "confirm_password": "differentpass",
            },
            follow_redirects=True,
        )
        assert response.status_code == 400

    def test_password_change_too_short(self, client, sample_user):
        """Test password change with too short new password."""
        # Login
        client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
        )

        # Try to change with short password
        response = client.post(
            "/auth/change-password",
            data={
                "current_password": "testpass123",
                "new_password": "short",
                "confirm_password": "short",
            },
            follow_redirects=True,
        )
        assert response.status_code == 400


class TestAuthenticationService:
    """Tests for authentication service functions."""

    def test_authenticate_success(self, db, sample_user):
        """Test authenticate function with valid credentials."""
        user = authenticate("testuser", "testpass123")
        assert user.login == "testuser"

    def test_authenticate_failure(self, db, sample_user):
        """Test authenticate function with invalid credentials."""
        import pytest

        with pytest.raises(AuthenticationError):
            authenticate("testuser", "wrongpass")

    def test_create_user(self, db):
        """Test user creation."""
        user = create_user("newuser", "newpass123")
        assert user.id is not None
        assert user.login == "newuser"
        assert user.check_password("newpass123")

    def test_create_duplicate_user(self, db, sample_user):
        """Test creating a user with existing login."""
        import pytest

        with pytest.raises(ValueError):
            create_user("testuser", "anotherpass")

    def test_change_password_service(self, db, sample_user):
        """Test change_password service function."""
        change_password(sample_user, "testpass123", "newpassword")
        assert sample_user.check_password("newpassword")
        assert sample_user.check_password("testpass123") is False

    def test_change_password_wrong_current(self, db, sample_user):
        """Test change_password with wrong current password."""
        import pytest

        with pytest.raises(AuthenticationError):
            change_password(sample_user, "wrongpass", "newpassword")


class TestPasswordRotation:
    """Bootstrap (national-ID) passwords must be rotated at first login."""

    def _student_with_profile(self, db):
        from app.infrastructure.database.models import StudentProfileModel, UserModel

        user = UserModel(login="09123456789")
        user.set_password("09123456789")
        user.must_change_password = True
        db.session.add(user)
        db.session.flush()
        db.session.add(
            StudentProfileModel(
                user_id=user.id,
                first_name="Test",
                last_name="Student",
                national_id="09123456789",
                mobile_phone="09120000009",
                birth_date=date(2000, 1, 1),
                gender="MALE",
            )
        )
        db.session.commit()
        return user

    def test_change_password_rejects_login_as_new(self, db, sample_user):
        with pytest.raises(ValueError, match="must not be"):
            change_password(sample_user, "testpass123", "testuser")

    def test_change_password_rejects_national_id_and_phone(self, db):
        user = self._student_with_profile(db)
        with pytest.raises(ValueError, match="must not be"):
            change_password(user, "09123456789", "09123456789")
        with pytest.raises(ValueError, match="must not be"):
            change_password(user, "09123456789", "09120000009")

    def test_change_password_clears_rotation_flag(self, db, sample_user):
        sample_user.must_change_password = True
        db.session.commit()
        change_password(sample_user, "testpass123", "brand-new-pass-1")
        assert sample_user.must_change_password is False
        assert sample_user.check_password("brand-new-pass-1")

    def test_flagged_login_redirects_to_change_password(self, client, db, sample_user):
        sample_user.must_change_password = True
        db.session.commit()
        resp = client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/auth/change-password" in resp.headers["Location"]

    def test_flagged_user_blocked_from_other_pages(self, client, db, sample_user):
        sample_user.must_change_password = True
        db.session.commit()
        client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
        )
        resp = client.get("/auth/dashboard", follow_redirects=False)
        assert resp.status_code == 302
        assert "/auth/change-password" in resp.headers["Location"]

    def test_rotation_completes_and_unlocks(self, client, db, sample_user):
        sample_user.must_change_password = True
        db.session.commit()
        client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
        )
        resp = client.post(
            "/auth/change-password",
            data={
                "current_password": "testpass123",
                "new_password": "brand-new-pass-2",
                "confirm_password": "brand-new-pass-2",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/auth/dashboard" in resp.headers["Location"]
        resp = client.get("/auth/dashboard")
        assert resp.status_code == 200

    def test_rotation_cannot_reuse_login(self, client, db, sample_user):
        sample_user.must_change_password = True
        db.session.commit()
        client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
        )
        resp = client.post(
            "/auth/change-password",
            data={
                "current_password": "testpass123",
                "new_password": "testuser",
                "confirm_password": "testuser",
            },
        )
        assert resp.status_code == 400


class TestLoginThrottling:
    """DB-backed brute-force protection shared across workers."""

    def test_repeated_failures_lock_account_temporarily(self, client, db, sample_user):
        for _ in range(5):
            resp = client.post(
                "/auth/login",
                data={"login": "testuser", "password": "wrongpass"},
            )
            assert resp.status_code == 401
        # Even the correct password is rejected while throttled.
        resp = client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
            follow_redirects=False,
        )
        assert resp.status_code == 429

    def test_success_within_budget_works(self, client, db, sample_user):
        for _ in range(4):
            client.post(
                "/auth/login",
                data={"login": "testuser", "password": "wrongpass"},
            )
        resp = client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_success_resets_failure_budget(self, client, db, sample_user):
        for _ in range(4):
            client.post(
                "/auth/login",
                data={"login": "testuser", "password": "wrongpass"},
            )
        client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
        )
        client.get("/auth/logout")
        # Budget was reset by the success: 4 more failures still allowed.
        for _ in range(4):
            resp = client.post(
                "/auth/login",
                data={"login": "testuser", "password": "wrongpass"},
            )
            assert resp.status_code == 401
        resp = client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_unknown_account_throttled_without_leak(self, client, db, sample_user):
        for _ in range(5):
            resp = client.post(
                "/auth/login",
                data={"login": "nosuchuser", "password": "wrongpass"},
            )
            assert resp.status_code == 401
        resp = client.post(
            "/auth/login",
            data={"login": "nosuchuser", "password": "wrongpass"},
        )
        assert resp.status_code == 429

    def test_attempts_are_recorded(self, client, db, sample_user):
        from app.infrastructure.database.models import LoginAttemptModel

        client.post(
            "/auth/login",
            data={"login": "testuser", "password": "wrongpass"},
        )
        assert (
            LoginAttemptModel.query.filter_by(
                login="testuser", successful=False
            ).count()
            == 1
        )


class TestProductionSecretValidation:
    """Production must refuse to boot on missing/default SECRET_KEY."""

    def test_production_rejects_default_secret(self, monkeypatch):
        from app import create_app
        from config import ProductionConfig

        monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "change-me")
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            create_app("production")

    def test_production_rejects_missing_secret(self, monkeypatch):
        from app import create_app
        from config import ProductionConfig

        monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "")
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            create_app("production")

    def test_production_boots_with_strong_secret(self, monkeypatch):
        from app import create_app
        from config import ProductionConfig

        monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "x" * 64)
        monkeypatch.setattr(
            ProductionConfig, "SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:"
        )
        monkeypatch.delenv("ENABLE_SCHEDULER", raising=False)
        app = create_app("production")
        assert app.config["SECRET_KEY"] == "x" * 64

    def test_production_rejects_bare_postgres_scheme(self, monkeypatch):
        from app import create_app
        from config import ProductionConfig

        monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "x" * 64)
        monkeypatch.setattr(
            ProductionConfig,
            "SQLALCHEMY_DATABASE_URI",
            "postgresql://u:p@localhost/db",
        )
        monkeypatch.delenv("ENABLE_SCHEDULER", raising=False)
        with pytest.raises(RuntimeError, match="postgresql\\+psycopg2"):
            create_app("production")

    def test_production_accepts_explicit_psycopg2_scheme(self, monkeypatch):
        from app import create_app
        from config import ProductionConfig

        monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "x" * 64)
        monkeypatch.setattr(
            ProductionConfig,
            "SQLALCHEMY_DATABASE_URI",
            "postgresql+psycopg2://u:p@localhost/db",
        )
        monkeypatch.delenv("ENABLE_SCHEDULER", raising=False)
        app = create_app("production")
        assert app.config["SQLALCHEMY_DATABASE_URI"].startswith(
            "postgresql+psycopg2://"
        )

    def test_development_keeps_convenient_fallback(self, monkeypatch):
        from app import create_app
        from config import DevelopmentConfig

        monkeypatch.setattr(
            DevelopmentConfig, "SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:"
        )
        app = create_app("development")
        assert app.config["SECRET_KEY"]
