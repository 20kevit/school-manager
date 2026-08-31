"""Public enrollment application service."""

from __future__ import annotations

from datetime import datetime

from app.extensions import db
from app.infrastructure.database.models import (
    AcademyClassModel,
    EnrollmentModel,
    RoleModel,
    StudentProfileModel,
    UserModel,
)


class PublicEnrollmentError(Exception):
    """Raised when a public enrollment operation fails."""


def submit_public_enrollment(
    first_name: str,
    last_name: str,
    national_id: str,
    mobile_phone: str,
    birth_date,
    gender: str,
    class_id: int,
) -> EnrollmentModel:
    """Submit a public enrollment application.

    Logic:
    - If national_id already exists as a StudentProfile, link the application
      to the existing student (do not create a new user).
    - If new, create a UserModel with is_active_user=False (pending state),
      assign STUDENT role, create StudentProfileModel.
    - Create an EnrollmentModel with status PENDING for the desired class.
    """
    academy_class = AcademyClassModel.query.get(class_id)
    if academy_class is None:
        raise PublicEnrollmentError("کلاس مورد نظر یافت نشد.")

    if academy_class.status in ("CANCELLED", "COMPLETED"):
        raise PublicEnrollmentError("این کلاس دیگر پذیرش ندارد.")

    existing_profile = StudentProfileModel.query.filter_by(
        national_id=national_id
    ).first()

    if existing_profile is not None:
        student_user_id = existing_profile.user_id

        existing_enrollment = (
            EnrollmentModel.query.filter_by(
                student_user_id=student_user_id,
                class_id=class_id,
            )
            .filter(EnrollmentModel.status.in_(["PENDING", "APPROVED"]))
            .first()
        )

        if existing_enrollment is not None:
            raise PublicEnrollmentError("شما قبلاً در این کلاس ثبت‌نام کرده‌اید.")
    else:
        user = UserModel(login=national_id)
        user.set_password(national_id)
        user.is_active_user = False
        db.session.add(user)
        db.session.flush()

        student_role = RoleModel.query.get("STUDENT")
        if student_role is None:
            student_role = RoleModel(name="STUDENT")
            db.session.add(student_role)
            db.session.flush()
        user.roles.append(student_role)

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
        db.session.flush()

        student_user_id = user.id

    enrollment = EnrollmentModel(
        student_user_id=student_user_id,
        class_id=class_id,
        status="PENDING",
        requested_at=datetime.now(),
    )
    db.session.add(enrollment)
    db.session.commit()

    return enrollment


def approve_and_activate_enrollment(enrollment: EnrollmentModel) -> EnrollmentModel:
    """Approve a public enrollment and activate the user account.

    - Activates the user account (is_active_user=True).
    - Sets password to national_id (if not already set differently).
    - Approves the enrollment.
    """
    from app.application.enrollment.enrollment_service import approve_enrollment

    user = UserModel.query.get(enrollment.student_user_id)
    if user is None:
        raise PublicEnrollmentError("کاربر یافت نشد.")

    profile = StudentProfileModel.query.filter_by(user_id=user.id).first()
    if profile is None:
        raise PublicEnrollmentError("پروفایل دانش‌آموز یافت نشد.")

    if not user.is_active_user:
        user.is_active_user = True
        user.set_password(profile.national_id)

    db.session.flush()

    approve_enrollment(enrollment)

    return enrollment
