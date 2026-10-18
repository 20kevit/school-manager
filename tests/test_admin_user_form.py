"""Regression tests for admin user creation UI/UX defects.

Covers:
* Student creation without an ignored password field (credential contract).
* Role preselection from the GET ?role= parameter.
* Preservation of safe form values after validation failures.
* Login-page credential instructions.
* Responsive user-list filter form (no conflicting inline grid styles).
* Mobile sidebar accessibility attributes.
* Dashboard KPI wording matching the underlying metric definition.
"""

import re

from app.infrastructure.database.models import UserModel


def _login_admin(client):
    client.post("/auth/login", data={"login": "admin", "password": "adminpass123"})


def _count_users(db):
    return UserModel.query.count()


STUDENT_DATA = {
    "login": "sara.ahmadi",
    "role": "STUDENT",
    "national_id": "0987654321",
    "first_name": "Sara",
    "last_name": "Ahmadi",
    "mobile_phone": "09131234567",
    "birth_date": "1385/05/15",
    "gender": "FEMALE",
}


class TestStudentCredentialContract:
    def test_create_student_without_password_succeeds(self, client, admin_user, db):
        """The admin route must not require a password the backend ignores."""
        _login_admin(client)
        resp = client.post("/admin/users/create", data=STUDENT_DATA)
        assert resp.status_code == 302

        user = UserModel.query.filter_by(login="sara.ahmadi").first()
        assert user is not None
        assert user.has_role("STUDENT")

        # Initial password is the national ID (hashed, never plaintext).
        assert user.check_password("0987654321") is True
        assert user.password_hash not in (None, "", "0987654321")

        # Mandatory first-login rotation stays enabled.
        assert user.must_change_password is True

    def test_create_student_preserves_admin_supplied_username(
        self, client, admin_user, db
    ):
        _login_admin(client)
        resp = client.post(
            "/admin/users/create",
            data={**STUDENT_DATA, "login": "custom-login-77"},
        )
        assert resp.status_code == 302
        assert UserModel.query.filter_by(login="custom-login-77").first() is not None
        assert UserModel.query.filter_by(login="0987654321").first() is None

    def test_password_field_absent_for_student_role(self, client, admin_user):
        """GET ?role=STUDENT must not ask for a password the backend ignores."""
        _login_admin(client)
        resp = client.get("/admin/users/create?role=STUDENT")
        body = resp.get_data(as_text=True)
        assert 'id="password-group" hidden' in body
        # The password input is rendered (for JS role switching) but is not
        # required and never needed for students.
        password_tag = body[
            body.index('name="password"') : body.index(
                ">", body.index('name="password"')
            )
        ]
        assert re.search(r"(?<!data-)required(?=[\s>])", password_tag) is None

    def test_student_form_shows_initial_password_note(self, client, admin_user):
        _login_admin(client)
        resp = client.get("/admin/users/create?role=STUDENT")
        body = resp.get_data(as_text=True)
        assert "رمز عبور اولیه" in body
        assert "کد ملی" in body
        assert "اولین ورود" in body

    def test_create_teacher_requires_password(self, client, admin_user, db):
        _login_admin(client)
        data = {
            "login": "newteacher",
            "role": "TEACHER",
            "password": "short",
            "national_id": "1234567890",
            "first_name": "Mmd",
            "last_name": "Ahmadi",
            "mobile_phone": "09121234567",
        }
        resp = client.post("/admin/users/create", data=data)
        assert resp.status_code == 200
        assert UserModel.query.filter_by(login="newteacher").first() is None

        data["password"] = "goodteacher123"
        resp = client.post("/admin/users/create", data=data)
        assert resp.status_code == 302
        user = UserModel.query.filter_by(login="newteacher").first()
        assert user is not None and user.has_role("TEACHER")
        assert user.check_password("goodteacher123") is True

    def test_create_parent_password_flow(self, client, admin_user, db):
        _login_admin(client)
        resp = client.post(
            "/admin/users/create",
            data={
                "login": "newparent",
                "password": "parentpass123",
                "role": "PARENT",
                "national_id": "1122334455",
                "first_name": "Reza",
                "last_name": "Rezaei",
                "mobile_phone": "09112233445",
            },
        )
        assert resp.status_code == 302
        user = UserModel.query.filter_by(login="newparent").first()
        assert user is not None and user.has_role("PARENT")
        assert user.must_change_password is not True

    def test_student_cannot_login_with_wrong_username_semantics(
        self, client, admin_user
    ):
        """Login page must not promise the national ID is the username."""
        _login_admin(client)
        client.post("/admin/users/create", data=STUDENT_DATA)
        resp = client.get("/auth/login")
        body = resp.get_data(as_text=True)
        assert "به عنوان نام کاربری" not in body
        assert "نام کاربری خود را از آکادمی دریافت کنید" in body
        assert "رمز عبور اولیه" in body or "کد ملی" in body


class TestRolePreselection:
    def test_get_student_role_preselected(self, client, admin_user):
        _login_admin(client)
        resp = client.get("/admin/users/create?role=STUDENT")
        body = resp.get_data(as_text=True)
        assert 'value="STUDENT" selected' in body
        assert 'id="student-fields"' in body

    def test_get_teacher_role_preselected(self, client, admin_user):
        _login_admin(client)
        resp = client.get("/admin/users/create?role=TEACHER")
        body = resp.get_data(as_text=True)
        assert 'value="TEACHER" selected' in body
        assert 'id="password-group"' in body

    def test_generic_form_has_no_preselected_role(self, client, admin_user):
        _login_admin(client)
        resp = client.get("/admin/users/create")
        body = resp.get_data(as_text=True)
        assert 'value="STUDENT" selected' not in body
        assert 'value="TEACHER" selected' not in body
        assert 'value="ADMIN" selected' not in body
        assert 'value="PARENT" selected' not in body

    def test_invalid_role_falls_back_safely(self, client, admin_user):
        _login_admin(client)
        resp = client.get("/admin/users/create?role=ROLE<script>")
        body = resp.get_data(as_text=True)
        assert resp.status_code == 200
        assert 'value="ROLE<script>" selected' not in body
        assert "پشتیبانی نمی‌شود" in body


class TestFormValuePreservation:
    def test_missing_student_fields_preserve_values(self, client, admin_user, db):
        _login_admin(client)
        resp = client.post(
            "/admin/users/create",
            data={
                k: v
                for k, v in STUDENT_DATA.items()
                if k not in ("last_name", "gender")
            },
        )
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert 'value="sara.ahmadi"' in body
        assert 'value="Sara"' in body
        assert 'value="0987654321"' in body
        assert 'value="09131234567"' in body
        assert 'value="1385/05/15"' in body
        assert 'value="STUDENT" selected' in body

    def test_invalid_birth_date_preserves_values(self, client, admin_user, db):
        _login_admin(client)
        resp = client.post(
            "/admin/users/create",
            data={**STUDENT_DATA, "birth_date": "1390/13/45"},
        )
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert 'value="sara.ahmadi"' in body
        assert 'value="Sara"' in body
        # The raw submitted value is preserved on the failed re-render.
        assert 'value="1390/13/45"' in body
        assert 'value="FEMALE" selected' in body

    def test_gender_select_preserves_submitted_value(self, client, admin_user, db):
        _login_admin(client)
        resp = client.post(
            "/admin/users/create",
            data={k: v for k, v in STUDENT_DATA.items() if k != ("last_name")},
        )
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert 'value="MALE" selected' not in body
        assert 'value="FEMALE" selected' in body

    def test_password_is_never_echoed(self, client, admin_user, db):
        _login_admin(client)
        resp = client.post(
            "/admin/users/create",
            data={
                "login": "leakcheck",
                "password": "Secret-Leak-Check-99",
                "role": "TEACHER",
                "first_name": "Ali",
                "last_name": "Karimi",
                "mobile_phone": "09121112233",
            },  # national_id missing -> validation error
        )
        body = resp.get_data(as_text=True)
        assert "Secret-Leak-Check-99" not in body
        assert 'value="leakcheck"' in body

    def test_invalid_role_preserves_values(self, client, admin_user, db):
        _login_admin(client)
        resp = client.post(
            "/admin/users/create",
            data={
                "login": "weirdrole",
                "role": "CUSTOMER",
                "first_name": "Ali",
            },
        )
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert 'value="weirdrole"' in body
        assert 'value="Ali"' in body

    def test_no_partial_account_after_failed_db_operation(self, client, admin_user, db):
        before = _count_users(db)
        _login_admin(client)
        client.post(
            "/admin/users/create",
            data={**STUDENT_DATA, "birth_date": "1390/13/01"},
        )
        assert _count_users(db) == before


class TestFilterFormResponsiveClass:
    def test_filter_form_uses_responsive_class(self, client, admin_user):
        _login_admin(client)
        resp = client.get("/admin/users")
        body = resp.get_data(as_text=True)
        assert 'class="user-filter-form"' in body
        assert 'style="grid-template-columns' not in body

    def test_filter_preserves_current_search_and_role(self, client, admin_user):
        _login_admin(client)
        resp = client.get("/admin/users?search=admin&role=ADMIN")
        body = resp.get_data(as_text=True)
        assert 'value="admin"' in body
        assert 'value="ADMIN" selected' in body


class TestDashboardKpiWording:
    def test_active_classes_label_matches_definition(self, client, admin_user):
        _login_admin(client)
        resp = client.get("/portal/admin")
        body = resp.get_data(as_text=True)
        assert "کلاس‌های فعال" in body
        assert "کلاس‌های در حال برگزاری" not in body

    def test_courses_subtext_explains_class_basis(self, client, admin_user):
        _login_admin(client)
        resp = client.get("/portal/admin")
        body = resp.get_data(as_text=True)
        assert "کلاس فعال و برنامه‌ریزی‌شده" in body

    def test_active_classes_link_keeps_status_filter(self, client, admin_user):
        _login_admin(client)
        resp = client.get("/academy/classes?status=ACTIVE")
        assert resp.status_code == 200


class TestSidebarAccessibilityMarkup:
    def test_menu_toggle_exposes_referenced_state(self, client, admin_user):
        _login_admin(client)
        resp = client.get("/admin/users")
        body = resp.get_data(as_text=True)
        assert 'aria-controls="sidebar"' in body
        assert 'aria-expanded="false"' in body
        assert 'id="menu-toggle"' in body
        assert 'id="sidebar"' in body

    def test_login_page_sidebar_markup(self, client):
        resp = client.get("/auth/login")
        body = resp.get_data(as_text=True)
        assert 'aria-controls="sidebar"' in body
        assert 'aria-expanded="false"' in body
