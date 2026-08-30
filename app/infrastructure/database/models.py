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


# ---------------------------------------------------------------------------
# P2 — Academy Structure
# ---------------------------------------------------------------------------


class CourseModel(db.Model):
    """Course table — reusable educational template."""

    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    num_sessions = db.Column(db.Integer, nullable=False, default=1)
    min_age = db.Column(db.Integer, nullable=True)
    max_age = db.Column(db.Integer, nullable=True)
    prerequisites = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    syllabus_items = db.relationship(
        "SyllabusItemModel",
        back_populates="course",
        order_by="SyllabusItemModel.order",
        lazy="select",
        cascade="all, delete-orphan",
    )
    classes = db.relationship(
        "AcademyClassModel",
        back_populates="course",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<CourseModel id={self.id} title={self.title!r}>"


class SyllabusItemModel(db.Model):
    """Syllabus item table — planned content for a course session."""

    __tablename__ = "syllabus_items"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    homework = db.Column(db.Text, default="")
    assessment = db.Column(db.Text, default="")

    course = db.relationship("CourseModel", back_populates="syllabus_items")

    __table_args__ = (
        db.UniqueConstraint("course_id", "order", name="uq_syllabus_course_order"),
    )

    def __repr__(self) -> str:
        return f"<SyllabusItemModel id={self.id} order={self.order}>"


class AcademyClassModel(db.Model):
    """Class table — an actual running class created from a Course."""

    __tablename__ = "academy_classes"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    capacity = db.Column(db.Integer, nullable=False, default=30)
    num_sessions = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="PLANNED")
    teacher_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    course = db.relationship("CourseModel", back_populates="classes")
    teacher = db.relationship("UserModel", foreign_keys=[teacher_user_id])
    schedule_entries = db.relationship(
        "ClassScheduleModel",
        back_populates="academy_class",
        order_by="ClassScheduleModel.weekday",
        lazy="select",
        cascade="all, delete-orphan",
    )
    sessions = db.relationship(
        "SessionModel",
        back_populates="academy_class",
        order_by="SessionModel.session_number",
        lazy="select",
        cascade="all, delete-orphan",
    )
    session_content_overrides = db.relationship(
        "ClassSessionContentModel",
        back_populates="academy_class",
        order_by="ClassSessionContentModel.session_number",
        lazy="select",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AcademyClassModel id={self.id} title={self.title!r}>"


class ClassScheduleModel(db.Model):
    """Weekly schedule entry table — one recurring weekly time slot."""

    __tablename__ = "class_schedules"

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(
        db.Integer, db.ForeignKey("academy_classes.id"), nullable=False
    )
    weekday = db.Column(db.String(10), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    academy_class = db.relationship(
        "AcademyClassModel", back_populates="schedule_entries"
    )

    __table_args__ = (
        db.UniqueConstraint("class_id", "weekday", name="uq_class_weekday"),
    )

    def __repr__(self) -> str:
        return (
            f"<ClassScheduleModel id={self.id} {self.weekday} "
            f"{self.start_time}-{self.end_time}>"
        )


class SessionModel(db.Model):
    """Session table — an individual occurrence of a class."""

    __tablename__ = "sessions"

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(
        db.Integer, db.ForeignKey("academy_classes.id"), nullable=False
    )
    session_number = db.Column(db.Integer, nullable=False)
    scheduled_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="SCHEDULED")
    title = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_rescheduled = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    academy_class = db.relationship("AcademyClassModel", back_populates="sessions")

    __table_args__ = (
        db.UniqueConstraint(
            "class_id", "session_number", name="uq_session_class_number"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<SessionModel id={self.id} class={self.class_id} "
            f"num={self.session_number} date={self.scheduled_date}>"
        )


class ClassSessionContentModel(db.Model):
    """Class-specific session content override table."""

    __tablename__ = "class_session_contents"

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(
        db.Integer, db.ForeignKey("academy_classes.id"), nullable=False
    )
    session_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    homework = db.Column(db.Text, nullable=True)
    assessment = db.Column(db.Text, nullable=True)

    academy_class = db.relationship(
        "AcademyClassModel", back_populates="session_content_overrides"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "class_id", "session_number", name="uq_class_content_session_number"
        ),
    )

    def __repr__(self) -> str:
        return f"<ClassSessionContentModel id={self.id} session={self.session_number}>"


# ---------------------------------------------------------------------------
# P3 — Enrollment
# ---------------------------------------------------------------------------


class EnrollmentModel(db.Model):
    """Enrollment table — represents a student's participation in a class."""

    __tablename__ = "enrollments"

    id = db.Column(db.Integer, primary_key=True)
    student_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    class_id = db.Column(
        db.Integer, db.ForeignKey("academy_classes.id"), nullable=False
    )
    status = db.Column(db.String(20), nullable=False, default="PENDING")
    requested_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    student = db.relationship("UserModel", foreign_keys=[student_user_id])
    academy_class = db.relationship(
        "AcademyClassModel", backref=db.backref("enrollments", lazy="select")
    )

    __table_args__ = (
        db.UniqueConstraint(
            "student_user_id",
            "class_id",
            "status",
            name="uq_enrollment_student_class_status",
        ),
        db.Index("ix_enrollment_student", "student_user_id"),
        db.Index("ix_enrollment_class", "class_id"),
        db.Index("ix_enrollment_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<EnrollmentModel id={self.id} student={self.student_user_id} "
            f"class={self.class_id} status={self.status}>"
        )


# ---------------------------------------------------------------------------
# P4 — Attendance
# ---------------------------------------------------------------------------


class AttendanceModel(db.Model):
    """Attendance table — records a student's presence for a session."""

    __tablename__ = "attendances"

    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(
        db.Integer, db.ForeignKey("enrollments.id"), nullable=False
    )
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    note = db.Column(db.Text, default="")
    recorded_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    enrollment = db.relationship(
        "EnrollmentModel", backref=db.backref("attendances", lazy="select")
    )
    session = db.relationship(
        "SessionModel", backref=db.backref("attendances", lazy="select")
    )
    recorder = db.relationship("UserModel", foreign_keys=[recorded_by])

    __table_args__ = (
        db.UniqueConstraint(
            "enrollment_id", "session_id", name="uq_attendance_enrollment_session"
        ),
        db.Index("ix_attendance_enrollment", "enrollment_id"),
        db.Index("ix_attendance_session", "session_id"),
        db.Index("ix_attendance_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<AttendanceModel id={self.id} enrollment={self.enrollment_id} "
            f"session={self.session_id} status={self.status}>"
        )
