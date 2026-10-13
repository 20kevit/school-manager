from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.application.auth.services import (
    AuthenticationError,
    change_password,
    get_client_ip,
    is_login_throttled,
    login_authenticated_user,
    logout_current_user,
    record_login_attempt,
)
from app.utils.flash import flash_safe_error

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.before_app_request
def enforce_password_rotation():
    """Force users with a system-assigned bootstrap password to rotate it.

    Runs for every request (blueprint-registered app-wide hook) but only
    redirects flagged accounts, and never blocks the rotation/logout flow
    itself or static assets.
    """
    if not current_user.is_authenticated:
        return None
    endpoint = request.endpoint or ""
    if endpoint in {
        "auth.change_password_view",
        "auth.logout",
        "auth.login",
        "static",
    }:
        return None
    if getattr(current_user, "must_change_password", False):
        flash("به دلایل امنیتی، ابتدا رمز عبور خود را تغییر دهید.", "warning")
        return redirect(url_for("auth.change_password_view"))
    return None


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page and handler."""
    if request.method == "POST":
        login_id = request.form.get("login", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        if not login_id or not password:
            flash("لطفاً نام کاربری و رمز عبور را وارد کنید.", "error")
            return render_template("auth/login.html"), 400

        ip_address = get_client_ip()
        if is_login_throttled(login_id, ip_address):
            flash(
                "تلاش‌های ناموفق زیاد است. لطفاً چند دقیقه بعد دوباره تلاش کنید.",
                "error",
            )
            return render_template("auth/login.html"), 429

        try:
            from app.application.auth.services import authenticate

            user = authenticate(login_id, password)
            record_login_attempt(login_id, ip_address, True)
            login_authenticated_user(user, remember=remember)
            if user.must_change_password:
                flash(
                    "به دلایل امنیتی، لطفاً رمز عبور خود را تغییر دهید.",
                    "warning",
                )
                return redirect(url_for("auth.change_password_view"))
            flash("ورود با موفقیت انجام شد.", "success")
            return redirect(url_for("auth.dashboard"))
        except AuthenticationError:
            record_login_attempt(login_id, ip_address, False)
            flash("نام کاربری یا رمز عبور نادرست است.", "error")
            return render_template("auth/login.html"), 401

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Log out the current user (POST only: GET would allow CSRF logout)."""
    logout_current_user()
    flash("شما با موفقیت خارج شدید.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    """Dashboard page for authenticated users — redirects to role-specific portal."""
    if current_user.has_any_role("ADMIN"):
        return redirect(url_for("portal.admin_dashboard"))
    if current_user.has_any_role("TEACHER"):
        return redirect(url_for("portal.teacher_dashboard"))
    if current_user.has_any_role("STUDENT"):
        return redirect(url_for("portal.student_dashboard"))
    if current_user.has_any_role("PARENT"):
        return redirect(url_for("portal.parent_dashboard"))
    return render_template("auth/dashboard.html")


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password_view():
    """Change password page and handler."""
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not current_password or not new_password:
            flash("لطفاً تمام فیلدها را پر کنید.", "error")
            return render_template("auth/change_password.html"), 400

        if new_password != confirm_password:
            flash("رمزهای عبور جدید مطابقت ندارند.", "error")
            return render_template("auth/change_password.html"), 400

        if len(new_password) < 6:
            flash("رمز عبور جدید باید حداقل ۶ کاراکتر باشد.", "error")
            return render_template("auth/change_password.html"), 400

        try:
            change_password(current_user, current_password, new_password)
            flash("رمز عبور با موفقیت تغییر کرد.", "success")
            return redirect(url_for("auth.dashboard"))
        except AuthenticationError:
            flash("رمز عبور فعلی نادرست است.", "error")
            return render_template("auth/change_password.html"), 400
        except ValueError as e:
            flash_safe_error(e)
            return render_template("auth/change_password.html"), 400

    return render_template("auth/change_password.html")


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """View and edit user profile."""
    from app.extensions import db
    from app.infrastructure.database.models import (
        ParentProfileModel,
        StudentProfileModel,
        TeacherProfileModel,
    )

    profile_obj = None
    profile_type = None
    profile_photo_url = None

    if current_user.has_any_role("STUDENT"):
        profile_obj = StudentProfileModel.query.filter_by(
            user_id=current_user.id
        ).first()
        profile_type = "student"
    elif current_user.has_any_role("TEACHER"):
        profile_obj = TeacherProfileModel.query.filter_by(
            user_id=current_user.id
        ).first()
        profile_type = "teacher"
    elif current_user.has_any_role("PARENT"):
        profile_obj = ParentProfileModel.query.filter_by(
            user_id=current_user.id
        ).first()
        profile_type = "parent"

    if profile_obj and profile_type == "student":
        from app.infrastructure.database.models import StoredFileModel

        photo = StoredFileModel.query.filter_by(
            entity_type="student_profile",
            entity_id=profile_obj.id,
            category="PROFILE_PHOTO",
            status="ACTIVE",
        ).first()
        if photo:
            profile_photo_url = f"/files/download/{photo.id}"

    if request.method == "POST" and profile_obj:
        try:
            first_name = request.form.get("first_name", "").strip()
            last_name = request.form.get("last_name", "").strip()
            mobile_phone = request.form.get("mobile_phone", "").strip()

            if not first_name or not last_name:
                flash("نام و نام خانوادگی الزامی است.", "error")
                return render_template(
                    "auth/profile.html",
                    profile=profile_obj,
                    profile_type=profile_type,
                    profile_photo=profile_photo_url,
                )

            profile_obj.first_name = first_name
            profile_obj.last_name = last_name
            if mobile_phone:
                profile_obj.mobile_phone = mobile_phone

            if profile_type == "student":
                from app.utils.date_utils import parse_jalali_date_or_none

                birth_date_str = request.form.get("birth_date", "")
                gender = request.form.get("gender", "")
                if birth_date_str:
                    try:
                        profile_obj.birth_date = parse_jalali_date_or_none(
                            birth_date_str
                        )
                    except ValueError as e:
                        flash_safe_error(e)
                        return render_template(
                            "auth/profile.html",
                            profile=profile_obj,
                            profile_type=profile_type,
                            profile_photo=profile_photo_url,
                        )
                if gender:
                    profile_obj.gender = gender

            db.session.commit()

            photo_file = request.files.get("profile_photo")
            if photo_file and photo_file.filename:
                _handle_profile_photo(profile_obj, profile_type, photo_file)

            flash("پروفایل با موفقیت به‌روزرسانی شد.", "success")
            return redirect(url_for("auth.profile"))
        except Exception:
            db.session.rollback()
            flash("خطا در به‌روزرسانی پروفایل.", "error")

    return render_template(
        "auth/profile.html",
        profile=profile_obj,
        profile_type=profile_type,
        profile_photo=profile_photo_url,
    )


def _handle_profile_photo(profile_obj, profile_type, photo_file):
    """Handle profile photo upload."""
    from app.extensions import db
    from app.infrastructure.database.models import StoredFileModel
    from app.infrastructure.storage import get_storage_backend

    allowed_extensions = {"jpg", "jpeg", "png", "webp"}
    max_size = 2 * 1024 * 1024  # 2 MB

    ext = (
        photo_file.filename.rsplit(".", 1)[-1].lower()
        if "." in photo_file.filename
        else ""
    )
    if ext not in allowed_extensions:
        flash("فرمت فایل مجاز نیست. فرمت‌های مجاز: JPG, PNG, WebP", "error")
        return

    photo_file.seek(0, 2)
    file_size = photo_file.tell()
    photo_file.seek(0)

    if file_size > max_size:
        flash("حجم فایل بیش از حد مجاز است (حداکثر ۲ مگابایت).", "error")
        return

    entity_type = f"{profile_type}_profile"

    old_photo = StoredFileModel.query.filter_by(
        entity_type=entity_type,
        entity_id=profile_obj.id,
        category="PROFILE_PHOTO",
        status="ACTIVE",
    ).first()

    storage = get_storage_backend()
    from app.application.file_management.file_service import sanitize_filename
    from app.infrastructure.storage import generate_storage_key

    storage_key = generate_storage_key("profile_photos", ext)
    storage.save_stream(storage_key, photo_file)

    import mimetypes

    mime_type = (
        mimetypes.guess_type(photo_file.filename)[0] or "application/octet-stream"
    )

    new_photo = StoredFileModel(
        original_filename=sanitize_filename(photo_file.filename),
        stored_filename=storage_key.split("/")[-1],
        extension=ext,
        mime_type=mime_type,
        file_size=file_size,
        storage_backend="local",
        storage_key=storage_key,
        status="ACTIVE",
        visibility="PRIVATE",
        category="PROFILE_PHOTO",
        uploader_user_id=current_user.id,
        entity_type=entity_type,
        entity_id=profile_obj.id,
    )
    db.session.add(new_photo)

    if old_photo:
        old_photo.status = "DELETED"

    db.session.commit()
