"""Tests for Phase 16 — Admin User Management & System Seeding."""

from datetime import date

import pytest

from app.application.auth.services import (
    assign_role,
    create_admin_user,
    create_parent_user,
    create_student_user,
    create_teacher_user,
    create_user,
    get_user_profile_data,
    link_parent_student,
    list_users,
    unlink_parent_student,
    update_user_profile,
)
from app.extensions import db
from app.infrastructure.database.models import (
    ParentProfileModel,
    RoleModel,
    StudentProfileModel,
    TeacherProfileModel,
    UserModel,
)

# ---------------------------------------------------------------------------
# Auth Services — user management helpers
# ---------------------------------------------------------------------------


class TestCreateTeacherUser:
    def test_creates_user_with_profile(self, db):
        user = create_teacher_user(
            login="t1",
            password="pass123",
            national_id="1111111111",
            first_name="Reza",
            last_name="Karimi",
            mobile_phone="09120000000",
        )
        assert user.id is not None
        assert user.has_role("TEACHER")
        profile = TeacherProfileModel.query.filter_by(user_id=user.id).first()
        assert profile is not None
        assert profile.first_name == "Reza"
        assert profile.national_id == "1111111111"

    def test_duplicate_login_raises(self, db):
        create_user("t_dup", "pass123")
        with pytest.raises(ValueError, match="already exists"):
            create_teacher_user(
                login="t_dup",
                password="pass123",
                national_id="1111111111",
                first_name="A",
                last_name="B",
                mobile_phone="09120000000",
            )


class TestCreateParentUser:
    def test_creates_user_with_profile(self, db):
        user = create_parent_user(
            login="p1",
            password="pass123",
            national_id="2222222222",
            first_name="Sara",
            last_name="Ahmadi",
            mobile_phone="09130000000",
        )
        assert user.id is not None
        assert user.has_role("PARENT")
        profile = ParentProfileModel.query.filter_by(user_id=user.id).first()
        assert profile is not None
        assert profile.first_name == "Sara"


class TestCreateAdminUser:
    def test_creates_admin_user(self, db):
        user = create_admin_user("adm1", "admin123")
        assert user.has_role("ADMIN")
        assert user.check_password("admin123")


class TestUpdateUserProfile:
    def test_update_student_profile(self, db):
        user = create_student_user(
            login="s1",
            national_id="3333333333",
            first_name="Ali",
            last_name="Rezaei",
            mobile_phone="09140000000",
            birth_date=date(2005, 3, 10),
            gender="MALE",
        )
        update_user_profile(user, first_name="Amir", last_name="Hosseini")
        profile = StudentProfileModel.query.filter_by(user_id=user.id).first()
        assert profile.first_name == "Amir"
        assert profile.last_name == "Hosseini"

    def test_update_teacher_profile(self, db):
        user = create_teacher_user(
            login="t2",
            password="pass123",
            national_id="4444444444",
            first_name="Mina",
            last_name="Nouri",
            mobile_phone="09150000000",
        )
        update_user_profile(user, first_name="Zahra")
        profile = TeacherProfileModel.query.filter_by(user_id=user.id).first()
        assert profile.first_name == "Zahra"

    def test_update_without_profile_raises(self, db):
        user = create_user("bare", "pass123")
        with pytest.raises(ValueError, match="does not have a profile"):
            update_user_profile(user, first_name="X")


class TestLinkParentStudent:
    def test_link(self, db):
        parent = create_parent_user(
            login="lp1",
            password="pass123",
            national_id="5555555555",
            first_name="P",
            last_name="L",
            mobile_phone="09160000000",
        )
        student = create_student_user(
            login="ls1",
            national_id="6666666666",
            first_name="S",
            last_name="L",
            mobile_phone="09170000000",
            birth_date=date(2010, 1, 1),
            gender="FEMALE",
        )
        link_parent_student(parent.id, student.id)
        profile = ParentProfileModel.query.filter_by(user_id=parent.id).first()
        assert any(c.user_id == student.id for c in profile.children)

    def test_unlink(self, db):
        parent = create_parent_user(
            login="lp2",
            password="pass123",
            national_id="7777777777",
            first_name="P2",
            last_name="L2",
            mobile_phone="09180000000",
        )
        student = create_student_user(
            login="ls2",
            national_id="8888888888",
            first_name="S2",
            last_name="L2",
            mobile_phone="09190000000",
            birth_date=date(2011, 2, 2),
            gender="MALE",
        )
        link_parent_student(parent.id, student.id)
        unlink_parent_student(parent.id, student.id)
        profile = ParentProfileModel.query.filter_by(user_id=parent.id).first()
        assert not any(c.user_id == student.id for c in profile.children)

    def test_link_nonexistent_parent_raises(self, db):
        student = create_student_user(
            login="ls3",
            national_id="9999999999",
            first_name="S3",
            last_name="L3",
            mobile_phone="09200000000",
            birth_date=date(2012, 3, 3),
            gender="MALE",
        )
        with pytest.raises(ValueError, match="Parent profile not found"):
            link_parent_student(9999, student.id)

    def test_link_nonexistent_student_raises(self, db):
        parent = create_parent_user(
            login="lp3",
            password="pass123",
            national_id="1010101010",
            first_name="P3",
            last_name="L3",
            mobile_phone="09210000000",
        )
        with pytest.raises(ValueError, match="Student profile not found"):
            link_parent_student(parent.id, 9999)


class TestGetUserProfileData:
    def test_student_profile_data(self, db):
        user = create_student_user(
            login="gpd1",
            national_id="1212121212",
            first_name="A",
            last_name="B",
            mobile_phone="09220000000",
            birth_date=date(2006, 4, 4),
            gender="MALE",
        )
        data = get_user_profile_data(user.id)
        assert data["profile_type"] == "student"
        assert data["profile"].first_name == "A"

    def test_nonexistent_user_raises(self, db):
        with pytest.raises(ValueError, match="User not found"):
            get_user_profile_data(9999)


class TestListUsers:
    def test_list_all(self, db):
        create_user("lu1", "pass123")
        create_user("lu2", "pass123")
        users, total = list_users()
        assert total >= 2

    def test_search_filter(self, db):
        create_user("searchable_xyz", "pass123")
        users, total = list_users(search="searchable_xyz")
        assert total == 1
        assert users[0].login == "searchable_xyz"

    def test_role_filter(self, db):
        create_user("rf1", "pass123")
        user2 = create_user("rf2", "pass123")
        assign_role(user2, "TEACHER")
        users, total = list_users(role_filter="TEACHER")
        assert all(u.has_role("TEACHER") for u in users)


# ---------------------------------------------------------------------------
# Flask seed CLI
# ---------------------------------------------------------------------------


class TestFlaskSeed:
    def test_seed_creates_roles_and_users(self, runner, db):
        result = runner.invoke(args=["seed"])
        assert result.exit_code == 0
        assert "Seed completed successfully" in result.output

        for role_name in ("ADMIN", "TEACHER", "STUDENT", "PARENT"):
            assert RoleModel.query.get(role_name) is not None

        assert UserModel.query.filter_by(login="admin").first() is not None
        assert UserModel.query.filter_by(login="teacher1").first() is not None
        assert UserModel.query.filter_by(login="student1").first() is not None
        assert UserModel.query.filter_by(login="parent1").first() is not None

    def test_seed_is_idempotent(self, runner, db):
        runner.invoke(args=["seed"])
        result = runner.invoke(args=["seed"])
        assert result.exit_code == 0
        assert "Already exists" in result.output


# ---------------------------------------------------------------------------
# Admin routes — UI tests (using direct URL paths)
# ---------------------------------------------------------------------------


def _login_admin(client):
    """Helper: log in as admin."""
    client.post("/auth/login", data={"login": "admin", "password": "adminpass123"})


def _login_teacher(client):
    """Helper: log in as teacher."""
    client.post("/auth/login", data={"login": "teacher", "password": "teacherpass123"})


class TestAdminUserList:
    def test_requires_admin(self, client, admin_user):
        _login_admin(client)
        resp = client.get("/admin/users")
        assert resp.status_code == 200

    def test_non_admin_forbidden(self, client, teacher_user):
        _login_teacher(client)
        resp = client.get("/admin/users")
        assert resp.status_code == 403

    def test_search(self, client, admin_user):
        _login_admin(client)
        resp = client.get("/admin/users?search=admin")
        assert resp.status_code == 200
        assert b"admin" in resp.data


class TestAdminUserCreate:
    def test_create_admin_user(self, client, admin_user):
        _login_admin(client)
        resp = client.post(
            "/admin/users/create",
            data={
                "login": "newadmin",
                "password": "newadmin123",
                "role": "ADMIN",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        user = UserModel.query.filter_by(login="newadmin").first()
        assert user is not None
        assert user.has_role("ADMIN")

    def test_create_teacher_user(self, client, admin_user):
        _login_admin(client)
        resp = client.post(
            "/admin/users/create",
            data={
                "login": "newteacher",
                "password": "newteacher123",
                "role": "TEACHER",
                "national_id": "1234567890",
                "first_name": "Mmd",
                "last_name": "Ahmadi",
                "mobile_phone": "09121234567",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        user = UserModel.query.filter_by(login="newteacher").first()
        assert user is not None
        assert user.has_role("TEACHER")

    def test_create_student_user(self, client, admin_user):
        _login_admin(client)
        resp = client.post(
            "/admin/users/create",
            data={
                "login": "newstudent",
                "password": "pass123456",
                "role": "STUDENT",
                "national_id": "0987654321",
                "first_name": "Sara",
                "last_name": "Ahmadi",
                "mobile_phone": "09131234567",
                "birth_date": "1385/05/15",
                "gender": "FEMALE",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_create_parent_user(self, client, admin_user):
        _login_admin(client)
        resp = client.post(
            "/admin/users/create",
            data={
                "login": "newparent",
                "password": "pass123456",
                "role": "PARENT",
                "national_id": "1122334455",
                "first_name": "Reza",
                "last_name": "Rezaei",
                "mobile_phone": "09112233445",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        user = UserModel.query.filter_by(login="newparent").first()
        assert user is not None
        assert user.has_role("PARENT")

    def test_create_missing_fields_shows_error(self, client, admin_user):
        _login_admin(client)
        resp = client.post(
            "/admin/users/create",
            data={"login": "", "password": "", "role": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200


class TestAdminUserEdit:
    def test_edit_get(self, client, admin_user, student_user):
        _login_admin(client)
        resp = client.get(f"/admin/users/{student_user.id}/edit")
        assert resp.status_code == 200

    def test_edit_nonexistent_user_redirects(self, client, admin_user):
        _login_admin(client)
        resp = client.get("/admin/users/9999/edit")
        assert resp.status_code == 302

    def test_update_profile(self, client, admin_user, student_user):
        _login_admin(client)
        resp = client.post(
            f"/admin/users/{student_user.id}/edit",
            data={
                "action": "update_profile",
                "first_name": "Amir",
                "last_name": "Hosseini",
                "national_id": "1234567890",
                "mobile_phone": "09121234567",
                "gender": "MALE",
                "birth_date": "1385/05/15",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_reset_password(self, client, admin_user, student_user):
        _login_admin(client)
        resp = client.post(
            f"/admin/users/{student_user.id}/edit",
            data={"action": "reset_password", "new_password": "newpass123"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        student_user_new = UserModel.query.get(student_user.id)
        assert student_user_new.check_password("newpass123")

    def test_toggle_active(self, client, admin_user, student_user):
        _login_admin(client)
        resp = client.post(
            f"/admin/users/{student_user.id}/edit",
            data={"action": "toggle_active"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        db.session.refresh(student_user)
        assert not student_user.is_active_user

    def test_short_password_rejected(self, client, admin_user, student_user):
        _login_admin(client)
        resp = client.post(
            f"/admin/users/{student_user.id}/edit",
            data={"action": "reset_password", "new_password": "short"},
            follow_redirects=True,
        )
        assert resp.status_code == 200


class TestParentStudentLinkingUI:
    def test_parent_edit_shows_linking_section(self, client, admin_user, parent_user):
        _login_admin(client)
        resp = client.get(f"/admin/users/{parent_user.id}/edit")
        assert resp.status_code == 200

    def test_link_student_from_edit(
        self, client, admin_user, parent_user, student_user
    ):
        _login_admin(client)
        resp = client.post(
            f"/admin/users/{parent_user.id}/edit",
            data={"action": "link_student", "student_user_id": student_user.id},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        profile = ParentProfileModel.query.filter_by(user_id=parent_user.id).first()
        assert any(c.user_id == student_user.id for c in profile.children)

    def test_unlink_student_from_edit(
        self, client, admin_user, parent_user, student_user
    ):
        link_parent_student(parent_user.id, student_user.id)
        _login_admin(client)
        resp = client.post(
            f"/admin/users/{parent_user.id}/edit",
            data={"action": "unlink_student", "student_user_id": student_user.id},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        profile = ParentProfileModel.query.filter_by(user_id=parent_user.id).first()
        assert not any(c.user_id == student_user.id for c in profile.children)
