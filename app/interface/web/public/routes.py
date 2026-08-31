"""Public routes — no login required."""

from __future__ import annotations

from flask import Blueprint, flash, render_template, request

from app.infrastructure.database.models import AcademyClassModel
from app.utils.date_utils import parse_jalali_date

public_bp = Blueprint("public", __name__, url_prefix="/enrollment")


@public_bp.route("/apply", methods=["GET", "POST"])
def public_apply():
    """Public enrollment application form — no login required."""
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        national_id = request.form.get("national_id", "").strip()
        mobile_phone = request.form.get("mobile_phone", "").strip()
        birth_date_str = request.form.get("birth_date", "").strip()
        gender = request.form.get("gender", "").strip()
        class_id_str = request.form.get("class_id", "").strip()

        if not all(
            [
                first_name,
                last_name,
                national_id,
                mobile_phone,
                birth_date_str,
                gender,
                class_id_str,
            ]
        ):
            flash("لطفاً تمام فیلدهای الزامی را پر کنید.", "error")
            return _render_form()

        try:
            birth_date = parse_jalali_date(birth_date_str)
        except ValueError as e:
            flash(str(e), "error")
            return _render_form()

        try:
            class_id = int(class_id_str)
        except ValueError, TypeError:
            flash("کلاس نامعتبر است.", "error")
            return _render_form()

        try:
            from app.application.enrollment.public_enrollment_service import (
                submit_public_enrollment,
            )

            submit_public_enrollment(
                first_name=first_name,
                last_name=last_name,
                national_id=national_id,
                mobile_phone=mobile_phone,
                birth_date=birth_date,
                gender=gender,
                class_id=class_id,
            )

            return render_template("enrollment/public_success.html")
        except Exception as e:
            flash(str(e), "error")
            return _render_form()

    return _render_form()


def _render_form():
    """Render the public enrollment form with active classes."""
    classes = (
        AcademyClassModel.query.filter(
            AcademyClassModel.status.in_(["PLANNED", "ACTIVE"])
        )
        .order_by(AcademyClassModel.title)
        .all()
    )
    return render_template("enrollment/public_apply.html", classes=classes)
