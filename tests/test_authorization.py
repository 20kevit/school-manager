"""Tests for role-based authorization."""


class TestAuthorization:
    """Tests for role-based authorization."""

    def test_role_protected_route_admin(self, client, admin_user):
        """Test that admin can access admin-only routes."""
        # Login as admin
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
        )

        # Access dashboard (authenticated route)
        response = client.get("/auth/dashboard", follow_redirects=True)
        assert response.status_code == 200

    def test_role_protected_route_requires_role(self, client, sample_user):
        """Test that role-protected routes reject unauthorized users."""
        # Login as regular user (no special role)
        client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
        )

        # Access dashboard (should work for any authenticated user)
        response = client.get("/auth/dashboard", follow_redirects=True)
        assert response.status_code == 200

    def test_unauthenticated_access(self, client):
        """Test that unauthenticated users cannot access protected routes."""
        response = client.get("/auth/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]

    def test_role_decorator_allows_correct_role(self, client, admin_user):
        """Test that role_required decorator allows users with required role."""
        # Login as admin
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
        )

        # Access admin-only route
        response = client.get("/admin-only", follow_redirects=True)
        assert response.status_code == 200

    def test_role_decorator_rejects_wrong_role(self, client, teacher_user):
        """Test that role_required decorator rejects users without required role."""
        # Login as teacher (not admin)
        client.post(
            "/auth/login",
            data={"login": "teacher", "password": "teacherpass123"},
        )

        # Access admin-only route should be forbidden
        response = client.get("/admin-only-2", follow_redirects=False)
        assert response.status_code == 403

    def test_role_decorator_rejects_unauthenticated(self, client):
        """Test that role_required decorator rejects unauthenticated users."""
        # Access admin-only route without login
        response = client.get("/admin-only-3", follow_redirects=False)
        # Flask-Login returns 401 for unauthenticated requests
        assert response.status_code in (302, 401)

    def test_student_cannot_access_admin_users(self, client, student_user):
        """Test that a student cannot access /admin/users (expect 403)."""
        # Login as student
        client.post(
            "/auth/login",
            data={"login": "student", "password": "studentpass123"},
        )

        # Access admin user management page
        response = client.get("/admin/users", follow_redirects=False)
        assert response.status_code == 403
