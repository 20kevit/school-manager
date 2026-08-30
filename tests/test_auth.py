"""Tests for authentication."""

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
