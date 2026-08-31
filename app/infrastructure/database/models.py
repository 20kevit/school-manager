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
# P23 — Academic Calendar & Semester Management
# ---------------------------------------------------------------------------


class AcademicYearModel(db.Model):
    """Academic year table (e.g., '1403-1404')."""

    __tablename__ = "academic_years"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    semesters = db.relationship(
        "SemesterModel",
        back_populates="academic_year",
        order_by="SemesterModel.start_date",
        lazy="select",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AcademicYearModel id={self.id} title={self.title!r}>"


class SemesterModel(db.Model):
    """Semester table — a term within an academic year."""

    __tablename__ = "semesters"

    id = db.Column(db.Integer, primary_key=True)
    academic_year_id = db.Column(
        db.Integer, db.ForeignKey("academic_years.id"), nullable=False
    )
    title = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    academic_year = db.relationship("AcademicYearModel", back_populates="semesters")
    classes = db.relationship(
        "AcademyClassModel",
        back_populates="semester",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<SemesterModel id={self.id} title={self.title!r}>"


class AcademicCalendarEventModel(db.Model):
    """Academic calendar event / holiday table."""

    __tablename__ = "academic_calendar_events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    is_recurring = db.Column(db.Boolean, nullable=False, default=False)
    description = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AcademicCalendarEventModel id={self.id} title={self.title!r}>"


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
    tuition = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    num_sessions = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="PLANNED")
    teacher_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    course = db.relationship("CourseModel", back_populates="classes")
    teacher = db.relationship("UserModel", foreign_keys=[teacher_user_id])
    semester = db.relationship("SemesterModel", back_populates="classes")
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
    edit_history = db.relationship(
        "SessionEditHistoryModel",
        back_populates="session",
        order_by="SessionEditHistoryModel.edited_at",
        lazy="select",
    )

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


class SessionEditHistoryModel(db.Model):
    """Session edit history — tracks changes to session date/time/content."""

    __tablename__ = "session_edit_history"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False)
    previous_date = db.Column(db.Date, nullable=True)
    new_date = db.Column(db.Date, nullable=True)
    previous_start_time = db.Column(db.Time, nullable=True)
    new_start_time = db.Column(db.Time, nullable=True)
    previous_end_time = db.Column(db.Time, nullable=True)
    new_end_time = db.Column(db.Time, nullable=True)
    previous_title = db.Column(db.String(200), nullable=True)
    new_title = db.Column(db.String(200), nullable=True)
    change_type = db.Column(db.String(20), nullable=False, default="EDIT")
    edited_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    edited_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    session = db.relationship("SessionModel", back_populates="edit_history")
    editor = db.relationship("UserModel", foreign_keys=[edited_by])

    def __repr__(self) -> str:
        return f"<SessionEditHistoryModel id={self.id} session={self.session_id}>"


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


# ---------------------------------------------------------------------------
# P5 — Learning Activities & Homework
# ---------------------------------------------------------------------------

ALLOWED_ACTIVITY_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "jpg",
    "jpeg",
    "png",
    "zip",
}

ALLOWED_ACTIVITY_MIMETYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "image/jpeg",
    "image/png",
    "application/zip",
}

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


class ActivityModel(db.Model):
    """Activity table — a learning activity (homework, project, quiz, etc.)."""

    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    requirement = db.Column(db.String(20), nullable=False, default="REQUIRED")
    deadline = db.Column(db.DateTime, nullable=True)
    max_score = db.Column(db.Numeric(10, 2), nullable=False, default=100)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey("academy_classes.id"), nullable=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    course = db.relationship(
        "CourseModel", backref=db.backref("activities", lazy="select")
    )
    academy_class = db.relationship(
        "AcademyClassModel", backref=db.backref("activities", lazy="select")
    )
    session = db.relationship(
        "SessionModel", backref=db.backref("activities", lazy="select")
    )

    __table_args__ = (
        db.Index("ix_activity_course", "course_id"),
        db.Index("ix_activity_class", "class_id"),
        db.Index("ix_activity_session", "session_id"),
        db.Index("ix_activity_type", "type"),
        db.Index("ix_activity_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<ActivityModel id={self.id} type={self.type} title={self.title!r}>"


class ActivitySubmissionModel(db.Model):
    """Activity submission table — a student's submission attempt for an activity."""

    __tablename__ = "activity_submissions"

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.id"), nullable=False)
    student_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    enrollment_id = db.Column(
        db.Integer, db.ForeignKey("enrollments.id"), nullable=False
    )
    text_content = db.Column(db.Text, default="")
    submitted_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="NOT_SUBMITTED")
    score = db.Column(db.Numeric(10, 2), nullable=True)
    feedback = db.Column(db.Text, default="")
    graded_at = db.Column(db.DateTime, nullable=True)
    graded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    activity = db.relationship(
        "ActivityModel", backref=db.backref("submissions", lazy="select")
    )
    student = db.relationship("UserModel", foreign_keys=[student_user_id])
    enrollment = db.relationship(
        "EnrollmentModel", backref=db.backref("submissions", lazy="select")
    )
    grader = db.relationship("UserModel", foreign_keys=[graded_by])

    __table_args__ = (
        db.Index("ix_submission_activity", "activity_id"),
        db.Index("ix_submission_student", "student_user_id"),
        db.Index("ix_submission_enrollment", "enrollment_id"),
        db.Index("ix_submission_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<ActivitySubmissionModel id={self.id} activity={self.activity_id} "
            f"student={self.student_user_id} version={self.version}>"
        )


class ActivityFileModel(db.Model):
    """Activity file table — files attached to a submission."""

    __tablename__ = "activity_files"

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(
        db.Integer, db.ForeignKey("activity_submissions.id"), nullable=False
    )
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    submission = db.relationship(
        "ActivitySubmissionModel",
        backref=db.backref("files", lazy="select", cascade="all, delete-orphan"),
    )

    __table_args__ = (db.Index("ix_activityfile_submission", "submission_id"),)

    def __repr__(self) -> str:
        return (
            f"<ActivityFileModel id={self.id} submission={self.submission_id} "
            f"filename={self.original_filename!r}>"
        )


# ---------------------------------------------------------------------------
# P6 — Finance & Tuition
# ---------------------------------------------------------------------------


class FinancialTransactionModel(db.Model):
    """Financial transaction table — the source of truth for student balances.

    Balance is derived: sum(signed_amount) for all ACTIVE transactions.
    Currency: Toman (internal representation as Numeric(12,2)).
    """

    __tablename__ = "financial_transactions"

    id = db.Column(db.Integer, primary_key=True)
    student_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, default="")
    reference_number = db.Column(db.String(100), default="")
    payment_method = db.Column(db.String(20), nullable=True)
    enrollment_id = db.Column(
        db.Integer, db.ForeignKey("enrollments.id"), nullable=True
    )
    class_id = db.Column(db.Integer, db.ForeignKey("academy_classes.id"), nullable=True)
    related_transaction_id = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="ACTIVE")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    student = db.relationship("UserModel", foreign_keys=[student_user_id])
    enrollment = db.relationship(
        "EnrollmentModel", backref=db.backref("financial_transactions", lazy="select")
    )
    academy_class = db.relationship(
        "AcademyClassModel", backref=db.backref("financial_transactions", lazy="select")
    )
    creator = db.relationship("UserModel", foreign_keys=[created_by])

    __table_args__ = (
        db.Index("ix_ft_student", "student_user_id"),
        db.Index("ix_ft_type", "transaction_type"),
        db.Index("ix_ft_category", "category"),
        db.Index("ix_ft_status", "status"),
        db.Index("ix_ft_enrollment", "enrollment_id"),
        db.Index("ix_ft_class", "class_id"),
        db.Index("ix_ft_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<FinancialTransactionModel id={self.id} "
            f"student={self.student_user_id} "
            f"type={self.transaction_type} "
            f"amount={self.amount}>"
        )


# ---------------------------------------------------------------------------
# P7 — Exams, Assessments & Grades
# ---------------------------------------------------------------------------


class AssessmentModel(db.Model):
    """Assessment table — an academic evaluation belonging to a class."""

    __tablename__ = "assessments"

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(
        db.Integer, db.ForeignKey("academy_classes.id"), nullable=False
    )
    type = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    scheduled_date = db.Column(db.Date, nullable=True)
    scheduled_time = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    max_score = db.Column(db.Numeric(10, 2), nullable=False, default=100)
    passing_score = db.Column(db.Numeric(10, 2), nullable=False, default=60)
    penalty_factor = db.Column(db.Numeric(4, 2), nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="DRAFT")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    academy_class = db.relationship(
        "AcademyClassModel", backref=db.backref("assessments", lazy="select")
    )
    creator = db.relationship("UserModel", foreign_keys=[created_by])

    __table_args__ = (
        db.Index("ix_assessment_class", "class_id"),
        db.Index("ix_assessment_type", "type"),
        db.Index("ix_assessment_status", "status"),
        db.Index("ix_assessment_date", "scheduled_date"),
    )

    VALID_TRANSITIONS = {
        "DRAFT": {"SCHEDULED", "CANCELLED"},
        "SCHEDULED": {"OPEN", "CANCELLED"},
        "OPEN": {"CLOSED", "CANCELLED"},
        "CLOSED": {"GRADED"},
    }

    def can_transition_to(self, new_status: str) -> bool:
        """Check if a status transition is valid."""
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())

    def __repr__(self) -> str:
        return (
            f"<AssessmentModel id={self.id} type={self.type} "
            f"title={self.title!r} class={self.class_id}>"
        )


class AssessmentResultModel(db.Model):
    """Assessment result table — a student's result in an assessment."""

    __tablename__ = "assessment_results"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(
        db.Integer, db.ForeignKey("assessments.id"), nullable=False
    )
    enrollment_id = db.Column(
        db.Integer, db.ForeignKey("enrollments.id"), nullable=False
    )
    student_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    score = db.Column(db.Numeric(10, 2), nullable=True)
    wrong_count = db.Column(db.Integer, nullable=True)
    max_score = db.Column(db.Numeric(10, 2), nullable=False, default=100)
    percentage = db.Column(db.Numeric(5, 2), nullable=True)
    result_status = db.Column(db.String(20), nullable=False, default="NOT_GRADED")
    presence_status = db.Column(db.String(20), nullable=False, default="PRESENT")
    pass_fail = db.Column(db.String(20), nullable=False, default="NOT_DETERMINED")
    comments = db.Column(db.Text, default="")
    graded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    graded_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    assessment = db.relationship(
        "AssessmentModel", backref=db.backref("results", lazy="select")
    )
    enrollment = db.relationship(
        "EnrollmentModel", backref=db.backref("assessment_results", lazy="select")
    )
    student = db.relationship("UserModel", foreign_keys=[student_user_id])
    grader = db.relationship("UserModel", foreign_keys=[graded_by])

    __table_args__ = (
        db.UniqueConstraint(
            "assessment_id",
            "enrollment_id",
            name="uq_result_assessment_enrollment",
        ),
        db.Index("ix_result_assessment", "assessment_id"),
        db.Index("ix_result_student", "student_user_id"),
        db.Index("ix_result_enrollment", "enrollment_id"),
        db.Index("ix_result_status", "result_status"),
        db.Index("ix_result_passfail", "pass_fail"),
    )

    def __repr__(self) -> str:
        return (
            f"<AssessmentResultModel id={self.id} assessment={self.assessment_id} "
            f"student={self.student_user_id} score={self.score}>"
        )


class GradeHistoryModel(db.Model):
    """Grade history table — audit trail for grade corrections."""

    __tablename__ = "grade_history"

    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(
        db.Integer, db.ForeignKey("assessment_results.id"), nullable=False
    )
    previous_score = db.Column(db.Numeric(10, 2), nullable=True)
    new_score = db.Column(db.Numeric(10, 2), nullable=True)
    previous_pass_fail = db.Column(db.String(20), nullable=False)
    new_pass_fail = db.Column(db.String(20), nullable=False)
    corrected_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reason = db.Column(db.Text, default="")
    corrected_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    result = db.relationship(
        "AssessmentResultModel",
        backref=db.backref(
            "grade_history", lazy="select", order_by="GradeHistoryModel.corrected_at"
        ),
    )
    corrector = db.relationship("UserModel", foreign_keys=[corrected_by])

    __table_args__ = (
        db.Index("ix_grade_history_result", "result_id"),
        db.Index("ix_grade_history_corrected_at", "corrected_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<GradeHistoryModel id={self.id} result={self.result_id} "
            f"prev={self.previous_score} new={self.new_score}>"
        )


# ---------------------------------------------------------------------------
# P21 — Advanced Grading & Transcripts
# ---------------------------------------------------------------------------


class GradingTemplateModel(db.Model):
    """Grading template table — defines weight distribution for assessment types."""

    __tablename__ = "grading_templates"

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(
        db.Integer, db.ForeignKey("academy_classes.id"), nullable=False
    )
    title = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    academy_class = db.relationship(
        "AcademyClassModel", backref=db.backref("grading_templates", lazy="select")
    )

    __table_args__ = (db.Index("ix_grading_template_class", "class_id"),)

    def __repr__(self) -> str:
        return (
            f"<GradingTemplateModel id={self.id} class={self.class_id} "
            f"title={self.title!r}>"
        )


class GradingComponentModel(db.Model):
    """Grading component table — a single weight in a grading template."""

    __tablename__ = "grading_components"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(
        db.Integer, db.ForeignKey("grading_templates.id"), nullable=False
    )
    assessment_type = db.Column(db.String(20), nullable=False)
    weight = db.Column(db.Numeric(5, 2), nullable=False)

    template = db.relationship(
        "GradingTemplateModel",
        backref=db.backref("components", lazy="select", cascade="all, delete-orphan"),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "template_id",
            "assessment_type",
            name="uq_grading_component_template_type",
        ),
        db.Index("ix_grading_component_template", "template_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<GradingComponentModel id={self.id} template={self.template_id} "
            f"type={self.assessment_type!r} weight={self.weight}>"
        )


# ---------------------------------------------------------------------------
# P9 — Notification System
# ---------------------------------------------------------------------------


class NotificationModel(db.Model):
    """Notification table — a single notification record."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    notification_type = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    recipient_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    priority = db.Column(db.String(10), nullable=False, default="NORMAL")
    template_id = db.Column(
        db.Integer, db.ForeignKey("notification_templates.id"), nullable=True
    )
    event_key = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="PENDING")
    scheduled_at = db.Column(db.DateTime, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    failed_at = db.Column(db.DateTime, nullable=True)
    failure_reason = db.Column(db.Text, default="")
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    recipient = db.relationship("UserModel", foreign_keys=[recipient_user_id])
    template = db.relationship("NotificationTemplateModel")

    __table_args__ = (
        db.Index("ix_notification_recipient", "recipient_user_id"),
        db.Index("ix_notification_status", "status"),
        db.Index("ix_notification_type", "notification_type"),
        db.Index("ix_notification_created_at", "created_at"),
        db.Index("ix_notification_event_key", "event_key"),
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationModel id={self.id} type={self.notification_type} "
            f"recipient={self.recipient_user_id} status={self.status}>"
        )


class NotificationDeliveryModel(db.Model):
    """Notification delivery table — tracks delivery per channel per notification."""

    __tablename__ = "notification_deliveries"

    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(
        db.Integer, db.ForeignKey("notifications.id"), nullable=False
    )
    channel = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="PENDING")
    provider_name = db.Column(db.String(50), default="")
    provider_message_id = db.Column(db.String(200), default="")
    failure_reason = db.Column(db.Text, default="")
    attempt_count = db.Column(db.Integer, nullable=False, default=0)
    sent_at = db.Column(db.DateTime, nullable=True)
    failed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    notification = db.relationship(
        "NotificationModel",
        backref=db.backref("deliveries", lazy="select", cascade="all, delete-orphan"),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "notification_id",
            "channel",
            name="uq_delivery_notification_channel",
        ),
        db.Index("ix_delivery_notification", "notification_id"),
        db.Index("ix_delivery_channel", "channel"),
        db.Index("ix_delivery_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationDeliveryModel id={self.id} "
            f"notification={self.notification_id} "
            f"channel={self.channel} status={self.status}>"
        )


class NotificationTemplateModel(db.Model):
    """Notification template table — reusable notification templates."""

    __tablename__ = "notification_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    notification_type = db.Column(db.String(40), nullable=False)
    channel = db.Column(db.String(20), nullable=False)
    subject = db.Column(db.String(200), default="")
    body = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    __table_args__ = (
        db.Index("ix_template_type", "notification_type"),
        db.Index("ix_template_channel", "channel"),
        db.Index("ix_template_active", "is_active"),
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationTemplateModel id={self.id} name={self.name!r} "
            f"type={self.notification_type} channel={self.channel}>"
        )


class NotificationPreferenceModel(db.Model):
    """Notification preference table — per-user channel/type preferences."""

    __tablename__ = "notification_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    notification_type = db.Column(db.String(40), nullable=False)
    channel = db.Column(db.String(20), nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    user = db.relationship(
        "UserModel", backref=db.backref("notification_preferences", lazy="select")
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "notification_type",
            "channel",
            name="uq_preference_user_type_channel",
        ),
        db.Index("ix_preference_user", "user_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationPreferenceModel id={self.id} user={self.user_id} "
            f"type={self.notification_type} channel={self.channel} "
            f"enabled={self.enabled}>"
        )


class InAppNotificationModel(db.Model):
    """In-app notification table — internal notifications visible in the portal."""

    __tablename__ = "in_app_notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    notification_id = db.Column(
        db.Integer, db.ForeignKey("notifications.id"), nullable=True
    )
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(
        db.String(40), nullable=False, default="IN_APP_MESSAGE"
    )
    link = db.Column(db.String(500), default="")
    read_status = db.Column(db.String(10), nullable=False, default="UNREAD")
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    user = db.relationship(
        "UserModel", backref=db.backref("in_app_notifications", lazy="select")
    )
    notification = db.relationship("NotificationModel")

    __table_args__ = (
        db.Index("ix_inapp_user", "user_id"),
        db.Index("ix_inapp_read_status", "read_status"),
        db.Index("ix_inapp_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<InAppNotificationModel id={self.id} user={self.user_id} "
            f"read={self.read_status}>"
        )


# ---------------------------------------------------------------------------
# File Management
# ---------------------------------------------------------------------------

# Allowed file extensions for general uploads
ALLOWED_UPLOAD_EXTENSIONS = frozenset(
    {"jpg", "jpeg", "png", "webp", "pdf", "txt", "csv"}
)

# Allowed MIME types for general uploads
ALLOWED_UPLOAD_MIMETYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
        "text/plain",
        "text/csv",
    }
)

# Max upload size: 5 MB (configurable via FILE_MAX_UPLOAD_SIZE)
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024


class StoredFileModel(db.Model):
    """Stored file table — metadata for uploaded files."""

    __tablename__ = "stored_files"

    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    extension = db.Column(db.String(20), nullable=False, default="")
    mime_type = db.Column(
        db.String(150), nullable=False, default="application/octet-stream"
    )
    file_size = db.Column(db.Integer, nullable=False, default=0)
    storage_backend = db.Column(db.String(20), nullable=False, default="local")
    storage_key = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="ACTIVE")
    visibility = db.Column(db.String(20), nullable=False, default="PRIVATE")
    category = db.Column(db.String(40), nullable=False, default="OTHER")
    uploader_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    # Generic association
    entity_type = db.Column(db.String(50), nullable=False, default="")
    entity_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )
    deleted_at = db.Column(db.DateTime, nullable=True)

    uploader = db.relationship(
        "UserModel", backref=db.backref("uploaded_files", lazy="select")
    )

    __table_args__ = (
        db.Index("ix_storedfile_uploader", "uploader_user_id"),
        db.Index("ix_storedfile_category", "category"),
        db.Index("ix_storedfile_status", "status"),
        db.Index("ix_storedfile_entity", "entity_type", "entity_id"),
        db.Index("ix_storedfile_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<StoredFileModel id={self.id} "
            f"original={self.original_filename!r} "
            f"category={self.category}>"
        )


# ---------------------------------------------------------------------------
# P24 — Teacher Salaries & Payroll
# ---------------------------------------------------------------------------


class TeacherContractModel(db.Model):
    """Teacher contract — defines payment terms for a teacher per class."""

    __tablename__ = "teacher_contracts"

    id = db.Column(db.Integer, primary_key=True)
    teacher_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("academy_classes.id"), nullable=True)
    payment_type = db.Column(db.String(30), nullable=False)
    rate = db.Column(db.Numeric(10, 2), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    teacher = db.relationship(
        "UserModel", backref=db.backref("contracts", lazy="select")
    )
    academy_class = db.relationship(
        "AcademyClassModel", backref=db.backref("contracts", lazy="select")
    )

    __table_args__ = (
        db.Index("ix_tc_teacher", "teacher_user_id"),
        db.Index("ix_tc_class", "class_id"),
        db.Index("ix_tc_active", "is_active"),
    )

    def __repr__(self) -> str:
        return (
            f"<TeacherContractModel id={self.id} "
            f"teacher={self.teacher_user_id} "
            f"type={self.payment_type} "
            f"rate={self.rate}>"
        )


class TeacherPaymentModel(db.Model):
    """Teacher payment — records a finalized payout to a teacher."""

    __tablename__ = "teacher_payments"

    id = db.Column(db.Integer, primary_key=True)
    teacher_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    gross_amount = db.Column(db.Numeric(12, 2), nullable=False)
    deductions = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    net_amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="PENDING")
    paid_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    teacher = db.relationship(
        "UserModel", backref=db.backref("payments", lazy="select")
    )

    __table_args__ = (
        db.Index("ix_tp_teacher", "teacher_user_id"),
        db.Index("ix_tp_period", "period_start", "period_end"),
        db.Index("ix_tp_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<TeacherPaymentModel id={self.id} "
            f"teacher={self.teacher_user_id} "
            f"gross={self.gross_amount} "
            f"status={self.status}>"
        )
