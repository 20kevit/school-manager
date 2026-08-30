"""Tests for Academy web UI authorization."""

from app.application.academy.course_service import create_course


class TestAcademyAuthorization:
    """Tests for academy route authorization."""

    def test_course_list_requires_admin(self, client, db):
        response = client.get("/academy/courses", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]

    def test_course_list_requires_admin_role(self, client, sample_user):
        client.post(
            "/auth/login",
            data={"login": "testuser", "password": "testpass123"},
        )
        response = client.get("/academy/courses", follow_redirects=False)
        assert response.status_code == 403

    def test_course_list_admin_access(self, client, admin_user):
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
        )
        response = client.get("/academy/courses")
        assert response.status_code == 200

    def test_class_list_requires_admin(self, client, db):
        response = client.get("/academy/classes", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]

    def test_class_list_admin_access(self, client, admin_user):
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
        )
        response = client.get("/academy/classes")
        assert response.status_code == 200

    def test_course_create_form_admin(self, client, admin_user):
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
        )
        response = client.get("/academy/courses/create")
        assert response.status_code == 200

    def test_course_create_post(self, client, admin_user):
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
        )
        response = client.post(
            "/academy/courses/create",
            data={
                "title": "Test Course",
                "description": "A test course",
                "num_sessions": "5",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

    def test_course_detail(self, client, admin_user, db):
        course = create_course(title="Detail Test", num_sessions=3)
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
        )
        response = client.get(f"/academy/courses/{course.id}")
        assert response.status_code == 200

    def test_class_create_form(self, client, admin_user, db):
        create_course(title="For Class", num_sessions=2)
        client.post(
            "/auth/login",
            data={"login": "admin", "password": "adminpass123"},
        )
        response = client.get("/academy/classes/create")
        assert response.status_code == 200
