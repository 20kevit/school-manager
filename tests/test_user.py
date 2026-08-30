"""Tests for User model."""

from app.infrastructure.database.models import RoleModel, UserModel


class TestUserModel:
    """Tests for UserModel."""

    def test_user_creation(self, db):
        """Test that a user can be created."""
        user = UserModel(login="newuser")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        assert user.id is not None
        assert user.login == "newuser"
        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_password_hashing(self, db):
        """Test that passwords are hashed, not stored in plaintext."""
        user = UserModel(login="hashtest")
        user.set_password("mypassword")
        db.session.add(user)
        db.session.commit()

        assert user.password_hash != "mypassword"
        assert len(user.password_hash) > 0

    def test_password_verification(self, db):
        """Test that password verification works."""
        user = UserModel(login="verifytest")
        user.set_password("correctpass")
        db.session.add(user)
        db.session.commit()

        assert user.check_password("correctpass") is True
        assert user.check_password("wrongpass") is False

    def test_unique_login(self, db):
        """Test that login identifiers are unique."""
        user1 = UserModel(login="unique1")
        user1.set_password("pass1")
        db.session.add(user1)
        db.session.commit()

        user2 = UserModel(login="unique1")
        user2.set_password("pass2")
        db.session.add(user2)

        from sqlalchemy.exc import IntegrityError

        try:
            db.session.commit()
            assert False, "Should have raised IntegrityError"
        except IntegrityError:
            db.session.rollback()

    def test_inactive_user(self, db):
        """Test that inactive users cannot log in."""
        user = UserModel(login="inactive", is_active_user=False)
        user.set_password("password")
        db.session.add(user)
        db.session.commit()

        assert user.is_active is False

    def test_user_roles(self, db):
        """Test user role management."""
        user = UserModel(login="roletest")
        user.set_password("password")
        role1 = RoleModel(name="ADMIN")
        role2 = RoleModel(name="TEACHER")
        db.session.add_all([user, role1, role2])
        db.session.flush()

        user.roles.append(role1)
        db.session.commit()

        assert user.has_role("ADMIN") is True
        assert user.has_role("TEACHER") is False
        assert user.has_any_role("ADMIN", "TEACHER") is True
        assert user.has_any_role("STUDENT") is False

    def test_user_repr(self, db):
        """Test user string representation."""
        user = UserModel(login="reprtest")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()

        assert "reprtest" in repr(user)
        assert str(user.id) in repr(user)
