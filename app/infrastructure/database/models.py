from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db

# Association table for parent-student many-to-many
parent_student = db.Table(
    "parent_student",
    db.Column(
        "parent_profile_id",
        db.Integer,
        db.ForeignKey("parent_profiles.id"),
        primary_key=True,
    ),
    db.Column(
        "student_profile_id",
        db.Integer,
        db.ForeignKey("student_profiles.id"),
        primary_key=True,
    ),
)

# Association table for user-roles many-to-many
user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column(
        "role_name",
        db.String(20),
        db.ForeignKey("roles.name"),
        primary_key=True,
    ),
)


class RoleModel(db.Model):
    """Role table for role-based access control."""

    __tablename__ = "roles"

    name = db.Column(db.String(20), primary_key=True)

    def __repr__(self) -> str:
        return f"<RoleModel {self.name!r}>"


class UserModel(UserMixin, db.Model):
    """User table for authentication with Flask-Login integration."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active_user = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    roles = db.relationship(
        "RoleModel",
        secondary=user_roles,
        lazy="select",
        backref=db.backref("users", lazy="select"),
    )

    student_profile = db.relationship(
        "StudentProfileModel",
        uselist=False,
        back_populates="user",
        lazy="select",
    )
    teacher_profile = db.relationship(
        "TeacherProfileModel",
        uselist=False,
        back_populates="user",
        lazy="select",
    )
    parent_profile = db.relationship(
        "ParentProfileModel",
        uselist=False,
        back_populates="user",
        lazy="select",
    )

    @property
    def is_active(self) -> bool:  # type: ignore[override]
        return self.is_active_user

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name: str) -> bool:
        return any(r.name == role_name for r in self.roles)

    def has_any_role(self, *role_names: str) -> bool:
        return any(r.name in role_names for r in self.roles)

    def __repr__(self) -> str:
        return f"<UserModel id={self.id} login={self.login!r}>"


class StudentProfileModel(db.Model):
    """Student profile table."""

    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    national_id = db.Column(db.String(10), unique=True, nullable=False, index=True)
    mobile_phone = db.Column(db.String(15), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)

    user = db.relationship("UserModel", back_populates="student_profile")

    def __repr__(self) -> str:
        return f"<StudentProfileModel id={self.id} national_id={self.national_id!r}>"


class TeacherProfileModel(db.Model):
    """Teacher profile table."""

    __tablename__ = "teacher_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    national_id = db.Column(db.String(10), unique=True, nullable=False, index=True)
    mobile_phone = db.Column(db.String(15), nullable=False)

    user = db.relationship("UserModel", back_populates="teacher_profile")

    def __repr__(self) -> str:
        return f"<TeacherProfileModel id={self.id} national_id={self.national_id!r}>"


class ParentProfileModel(db.Model):
    """Parent profile table."""

    __tablename__ = "parent_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    national_id = db.Column(db.String(10), unique=True, nullable=False, index=True)
    mobile_phone = db.Column(db.String(15), nullable=False)

    user = db.relationship("UserModel", back_populates="parent_profile")
    children = db.relationship(
        "StudentProfileModel",
        secondary=parent_student,
        backref=db.backref("parents", lazy="select"),
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<ParentProfileModel id={self.id} national_id={self.national_id!r}>"
