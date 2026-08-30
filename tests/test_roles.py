"""Tests for roles."""

from app.infrastructure.database.models import RoleModel, UserModel


class TestRoles:
    """Tests for role management."""

    def test_single_role(self, db):
        """Test assigning a single role to a user."""
        user = UserModel(login="singlerole")
        user.set_password("password")
        role = RoleModel(name="STUDENT")
        db.session.add_all([user, role])
        db.session.flush()

        user.roles.append(role)
        db.session.commit()

        assert len(user.roles) == 1
        assert user.has_role("STUDENT") is True

    def test_multiple_roles(self, db):
        """Test assigning multiple roles to a user."""
        user = UserModel(login="multirole")
        user.set_password("password")
        role1 = RoleModel(name="TEACHER")
        role2 = RoleModel(name="PARENT")
        db.session.add_all([user, role1, role2])
        db.session.flush()

        user.roles.append(role1)
        user.roles.append(role2)
        db.session.commit()

        assert len(user.roles) == 2
        assert user.has_role("TEACHER") is True
        assert user.has_role("PARENT") is True
        assert user.has_any_role("TEACHER", "PARENT") is True

    def test_all_initial_roles(self, db):
        """Test that all initial roles can be created."""
        roles = ["ADMIN", "TEACHER", "STUDENT", "PARENT"]
        for role_name in roles:
            role = RoleModel(name=role_name)
            db.session.add(role)
        db.session.commit()

        for role_name in roles:
            role = RoleModel.query.get(role_name)
            assert role is not None

    def test_role_backref(self, db):
        """Test role backref to users."""
        user1 = UserModel(login="user1")
        user1.set_password("pass1")
        user2 = UserModel(login="user2")
        user2.set_password("pass2")
        role = RoleModel(name="ADMIN")
        db.session.add_all([user1, user2, role])
        db.session.flush()

        user1.roles.append(role)
        user2.roles.append(role)
        db.session.commit()

        assert len(role.users) == 2
