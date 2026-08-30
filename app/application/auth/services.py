from __future__ import annotations

from flask_login import login_user, logout_user

from app.extensions import db
from app.infrastructure.database.models import RoleModel, UserModel


class AuthenticationError(Exception):
    """Raised when authentication fails."""


class AuthorizationError(Exception):
    """Raised when authorization fails."""


def authenticate(login: str, password: str) -> UserModel:
    """Authenticate a user by login and password.

    Returns the authenticated UserModel on success.
    Raises AuthenticationError on failure.
    """
    user = UserModel.query.filter_by(login=login).first()

    if user is None:
        raise AuthenticationError("Invalid login or password.")

    if not user.is_active:
        raise AuthenticationError("Account is disabled.")

    if not user.check_password(password):
        raise AuthenticationError("Invalid login or password.")

    return user


def login_authenticated_user(user: UserModel, remember: bool = False) -> None:
    """Log in an already-authenticated user (creates session)."""
    login_user(user, remember=remember)


def logout_current_user() -> None:
    """Log out the current user (destroys session)."""
    logout_user()


def change_password(user: UserModel, current_password: str, new_password: str) -> None:
    """Change a user's password.

    Raises AuthenticationError if the current password is incorrect.
    """
    if not user.check_password(current_password):
        raise AuthenticationError("Current password is incorrect.")

    user.set_password(new_password)
    db.session.commit()


def create_user(login: str, password: str) -> UserModel:
    """Create a new user with the given login and password.

    Raises ValueError if the login already exists.
    """
    existing = UserModel.query.filter_by(login=login).first()
    if existing is not None:
        raise ValueError(f"User with login {login!r} already exists.")

    user = UserModel(login=login)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def assign_role(user: UserModel, role_name: str) -> None:
    """Assign a role to a user."""
    if user.has_role(role_name):
        return

    role = RoleModel.query.get(role_name)
    if role is None:
        role = RoleModel(name=role_name)
        db.session.add(role)

    user.roles.append(role)
    db.session.commit()


def remove_role(user: UserModel, role_name: str) -> None:
    """Remove a role from a user."""
    user.roles = [r for r in user.roles if r.name != role_name]
    db.session.commit()


def create_student_user(
    login: str,
    national_id: str,
    first_name: str,
    last_name: str,
    mobile_phone: str,
    birth_date,
    gender: str,
) -> UserModel:
    """Create a new student user with initial credentials.

    Initial password is the national_id.
    """
    from app.infrastructure.database.models import StudentProfileModel

    user = create_user(login, national_id)
    assign_role(user, "STUDENT")

    profile = StudentProfileModel(
        user_id=user.id,
        first_name=first_name,
        last_name=last_name,
        national_id=national_id,
        mobile_phone=mobile_phone,
        birth_date=birth_date,
        gender=gender,
    )
    db.session.add(profile)
    db.session.commit()
    return user
