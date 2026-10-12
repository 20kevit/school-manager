from __future__ import annotations

from datetime import datetime, timedelta

from flask import current_app, request
from flask_login import login_user, logout_user

from app.extensions import db
from app.infrastructure.database.models import LoginAttemptModel, RoleModel, UserModel


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


def _predictable_password_values(user: UserModel) -> set[str]:
    """Personal identifiers that must never be accepted as a password."""
    values = {user.login or ""}
    for profile in (
        user.student_profile,
        user.teacher_profile,
        user.parent_profile,
    ):
        if profile is None:
            continue
        values.add(getattr(profile, "national_id", "") or "")
        values.add(getattr(profile, "mobile_phone", "") or "")
    return {v for v in values if v}


def change_password(user: UserModel, current_password: str, new_password: str) -> None:
    """Change a user's password.

    Raises AuthenticationError if the current password is incorrect.
    Raises ValueError if the new password is a predictable personal
    identifier (login, national ID, phone number).
    Clears the must_change_password flag on success.
    """
    if not user.check_password(current_password):
        raise AuthenticationError("Current password is incorrect.")

    if new_password in _predictable_password_values(user):
        raise ValueError(
            "New password must not be your login, national ID, or phone number."
        )

    user.set_password(new_password)
    user.must_change_password = False
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

    Initial password is the national_id. The account is flagged
    must_change_password so the bootstrap credential is rotated at
    first login and can never remain a standing password.
    """
    from app.infrastructure.database.models import StudentProfileModel

    user = create_user(login, national_id)
    user.must_change_password = True
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


def create_teacher_user(
    login: str,
    password: str,
    national_id: str,
    first_name: str,
    last_name: str,
    mobile_phone: str,
) -> UserModel:
    """Create a new teacher user with profile."""
    from app.infrastructure.database.models import TeacherProfileModel

    user = create_user(login, password)
    assign_role(user, "TEACHER")

    profile = TeacherProfileModel(
        user_id=user.id,
        first_name=first_name,
        last_name=last_name,
        national_id=national_id,
        mobile_phone=mobile_phone,
    )
    db.session.add(profile)
    db.session.commit()
    return user


def create_parent_user(
    login: str,
    password: str,
    national_id: str,
    first_name: str,
    last_name: str,
    mobile_phone: str,
) -> UserModel:
    """Create a new parent user with profile."""
    from app.infrastructure.database.models import ParentProfileModel

    user = create_user(login, password)
    assign_role(user, "PARENT")

    profile = ParentProfileModel(
        user_id=user.id,
        first_name=first_name,
        last_name=last_name,
        national_id=national_id,
        mobile_phone=mobile_phone,
    )
    db.session.add(profile)
    db.session.commit()
    return user


def create_admin_user(login: str, password: str) -> UserModel:
    """Create a new admin user."""
    user = create_user(login, password)
    assign_role(user, "ADMIN")
    return user


def update_user_profile(user: UserModel, **kwargs) -> None:
    """Update a user's profile fields.

    Supported kwargs: first_name, last_name, mobile_phone, birth_date, gender,
    national_id (for student/teacher/parent profiles).
    """
    from app.infrastructure.database.models import (
        ParentProfileModel,
        StudentProfileModel,
        TeacherProfileModel,
    )

    profile = None
    if user.has_role("STUDENT"):
        profile = StudentProfileModel.query.filter_by(user_id=user.id).first()
    elif user.has_role("TEACHER"):
        profile = TeacherProfileModel.query.filter_by(user_id=user.id).first()
    elif user.has_role("PARENT"):
        profile = ParentProfileModel.query.filter_by(user_id=user.id).first()

    if profile is None:
        raise ValueError("User does not have a profile.")

    for field in ("first_name", "last_name", "mobile_phone", "national_id"):
        if field in kwargs and kwargs[field] is not None:
            setattr(profile, field, kwargs[field])

    if "birth_date" in kwargs and kwargs["birth_date"] is not None:
        if hasattr(profile, "birth_date"):
            profile.birth_date = kwargs["birth_date"]

    if "gender" in kwargs and kwargs["gender"] is not None:
        if hasattr(profile, "gender"):
            profile.gender = kwargs["gender"]

    db.session.commit()


def link_parent_student(parent_user_id: int, student_user_id: int) -> None:
    """Link a student to a parent profile."""
    from app.infrastructure.database.models import (
        ParentProfileModel,
        StudentProfileModel,
    )

    parent_profile = ParentProfileModel.query.filter_by(user_id=parent_user_id).first()
    if parent_profile is None:
        raise ValueError("Parent profile not found.")

    student_profile = StudentProfileModel.query.filter_by(
        user_id=student_user_id
    ).first()
    if student_profile is None:
        raise ValueError("Student profile not found.")

    if student_profile not in parent_profile.children:
        parent_profile.children.append(student_profile)
        db.session.commit()


def unlink_parent_student(parent_user_id: int, student_user_id: int) -> None:
    """Remove a student from a parent's linked children."""
    from app.infrastructure.database.models import ParentProfileModel

    parent_profile = ParentProfileModel.query.filter_by(user_id=parent_user_id).first()
    if parent_profile is None:
        raise ValueError("Parent profile not found.")

    parent_profile.children = [
        c for c in parent_profile.children if c.user_id != student_user_id
    ]
    db.session.commit()


def get_user_profile_data(user_id: int) -> dict:
    """Get user with profile data for admin editing."""
    from app.infrastructure.database.models import (
        ParentProfileModel,
        StudentProfileModel,
        TeacherProfileModel,
    )

    user = UserModel.query.get(user_id)
    if user is None:
        raise ValueError("User not found.")

    profile = None
    profile_type = None
    if user.has_role("STUDENT"):
        profile = StudentProfileModel.query.filter_by(user_id=user.id).first()
        profile_type = "student"
    elif user.has_role("TEACHER"):
        profile = TeacherProfileModel.query.filter_by(user_id=user.id).first()
        profile_type = "teacher"
    elif user.has_role("PARENT"):
        profile = ParentProfileModel.query.filter_by(user_id=user.id).first()
        profile_type = "parent"

    return {
        "user": user,
        "profile": profile,
        "profile_type": profile_type,
    }


def list_users(
    search: str = "",
    role_filter: str = "",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[UserModel], int]:
    """List users with optional search and role filter.

    Returns (users, total_count).
    """
    query = UserModel.query

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(UserModel.login.ilike(search_pattern))

    if role_filter:
        from app.infrastructure.database.models import user_roles

        query = query.join(user_roles).filter(user_roles.c.role_name == role_filter)

    query = query.order_by(UserModel.id)
    total = query.count()
    users = query.offset((page - 1) * per_page).limit(per_page).all()
    return users, total


# ---------------------------------------------------------------------------
# Login throttling (DB-backed, shared across Gunicorn workers)
# ---------------------------------------------------------------------------


def _throttle_config(name: str, default: int) -> int:
    # contextlib.suppress (not try/except) so the ruff formatter cannot
    # rewrite the exception tuple into invalid syntax.
    import contextlib

    with contextlib.suppress(RuntimeError, ValueError, TypeError):
        return int(current_app.config.get(name, default))
    return default


def get_client_ip() -> str:
    """Best-effort client IP behind Cloudflare/Nginx.

    Prefers CF-Connecting-IP (set by Cloudflare, passed through by our
    Nginx) and falls back to the direct peer. Headers are spoofable by
    clients reaching the origin directly, so throttling ALSO keys on the
    account login, which cannot be spoofed. Never use this IP for
    authorization decisions.
    """
    try:
        forwarded = request.headers.get("CF-Connecting-IP", "").strip()
    except RuntimeError:
        forwarded = ""
    if forwarded:
        return forwarded[:45]
    try:
        return (request.remote_addr or "unknown")[:45]
    except RuntimeError:
        return "unknown"


def _throttle_window_start() -> datetime:
    minutes = _throttle_config("LOGIN_THROTTLE_WINDOW_MINUTES", 15)
    return datetime.now() - timedelta(minutes=minutes)


def is_login_throttled(login: str, ip_address: str) -> bool:
    """True when recent failures exceed the per-account or per-IP budget.

    Temporary by design (sliding window) — accounts are never permanently
    locked, so this cannot be abused for denial of service.
    """
    window_start = _throttle_window_start()
    max_per_account = _throttle_config("LOGIN_THROTTLE_MAX_ATTEMPTS", 5)
    max_per_ip = _throttle_config("LOGIN_THROTTLE_MAX_PER_IP", 30)

    base = LoginAttemptModel.query.filter(
        LoginAttemptModel.successful.is_(False),
        LoginAttemptModel.attempted_at >= window_start,
    )
    account_failures = base.filter(
        LoginAttemptModel.login == login.strip().lower()
    ).count()
    if account_failures >= max_per_account:
        return True
    ip_failures = base.filter(LoginAttemptModel.ip_address == ip_address).count()
    return ip_failures >= max_per_ip


def record_login_attempt(login: str, ip_address: str, successful: bool) -> None:
    """Persist a login attempt and prune entries outside the window."""
    normalized = login.strip().lower()
    db.session.add(
        LoginAttemptModel(
            login=normalized, ip_address=ip_address, successful=successful
        )
    )
    if successful:
        # A success resets the account's failure budget.
        LoginAttemptModel.query.filter_by(login=normalized, successful=False).delete()
    else:
        db.session.query(LoginAttemptModel).filter(
            LoginAttemptModel.attempted_at < _throttle_window_start()
        ).delete()
    db.session.commit()
