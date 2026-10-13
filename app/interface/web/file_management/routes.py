"""File Management routes — admin, upload, download, API."""

from __future__ import annotations

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required

from app.application.file_management.file_service import (
    FileError,
    authorize_entity_attachment,
    can_access_file,
    can_delete_file,
    can_download_file,
    delete_file,
    find_orphan_files,
    get_file_metadata,
    get_file_stream,
    list_files,
    upload_file,
)
from app.infrastructure.database.models import StoredFileModel
from app.interface.web.decorators import role_required
from app.utils.flash import flash_safe_error


def _safe_back_redirect(fallback_endpoint: str = "auth.dashboard"):
    """Redirect back to the originating page without an open-redirect hole.

    Same-origin relative paths are honored; anything else (absolute
    URLs, protocol-relative URLs, other hosts) falls back internally.
    """
    from urllib.parse import urlparse

    referrer = request.referrer or ""
    if referrer:
        try:
            parsed = urlparse(referrer)
            # Same-origin absolute URLs: no scheme change, same netloc as host.
            if parsed.scheme in ("http", "https") and parsed.netloc == request.host:
                return redirect(parsed.path or "/")
            # Relative paths (no scheme, no netloc).
            if not parsed.scheme and not parsed.netloc and parsed.path.startswith("/"):
                return redirect(parsed.path)
        except Exception:
            pass
    return redirect(url_for(fallback_endpoint))


file_bp = Blueprint("file_management", __name__, url_prefix="/files")


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------


@file_bp.route("/admin")
@login_required
@role_required("ADMIN")
def admin_file_list():
    """List all files with filters."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    # Clamp pagination: unbounded LIMIT is a DB/memory DoS vector, and
    # non-positive values have surprising LIMIT semantics.
    page = max(page or 1, 1)
    per_page = min(max(per_page or 20, 1), 100)
    category = request.args.get("category", type=str)
    status = request.args.get("status", "ACTIVE", type=str)
    uploader = request.args.get("uploader", type=int)
    search = request.args.get("search", "", type=str)

    files, total = list_files(
        category=category,
        status=status,
        uploader_user_id=uploader,
        page=page,
        per_page=per_page,
    )

    if search:
        search_lower = search.lower()
        files = [f for f in files if search_lower in f.original_filename.lower()]

    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1

    categories = [
        "PROFILE_PHOTO",
        "STUDENT_DOCUMENT",
        "ACTIVITY_ATTACHMENT",
        "ACTIVITY_SUBMISSION",
        "FINANCE_DOCUMENT",
        "EDUCATIONAL_MATERIAL",
        "OTHER",
    ]

    return render_template(
        "file_management/admin_list.html",
        files=files,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        categories=categories,
        selected_category=category,
        selected_status=status,
        selected_uploader=uploader,
        search=search,
    )


@file_bp.route("/admin/<int:file_id>")
@login_required
@role_required("ADMIN")
def admin_file_detail(file_id):
    """View file metadata."""
    from app.infrastructure.database.models import UserModel

    record = StoredFileModel.query.get(file_id)
    if record is None:
        flash("File not found.", "error")
        return redirect(url_for("file_management.admin_file_list"))

    uploader = None
    if record.uploader_user_id:
        uploader = UserModel.query.get(record.uploader_user_id)

    return render_template(
        "file_management/admin_detail.html",
        file_record=record,
        uploader=uploader,
    )


@file_bp.route("/admin/<int:file_id>/delete", methods=["POST"])
@login_required
@role_required("ADMIN")
def admin_delete_file(file_id):
    """Delete/deactivate a file."""
    record = StoredFileModel.query.get(file_id)
    if record is None:
        flash("File not found.", "error")
        return redirect(url_for("file_management.admin_file_list"))

    if not can_delete_file(current_user, record):
        flash("Access denied.", "error")
        return redirect(url_for("file_management.admin_file_list"))

    try:
        delete_file(file_id)
        flash("File deleted.", "success")
    except FileError as e:
        flash_safe_error(e)

    return redirect(url_for("file_management.admin_file_list"))


@file_bp.route("/admin/orphans")
@login_required
@role_required("ADMIN")
def admin_orphans():
    """List orphan files."""
    orphans = find_orphan_files()
    return render_template(
        "file_management/admin_orphans.html",
        orphans=orphans,
    )


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------


@file_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    """Handle file upload via form submission."""
    uploaded_files = request.files.getlist("files")
    if not uploaded_files:
        flash("No files selected.", "error")
        return _safe_back_redirect()

    category = request.form.get("category", "OTHER")
    entity_type = request.form.get("entity_type", "")
    entity_id = request.form.get("entity_id", type=int)
    visibility = request.form.get("visibility", "PRIVATE")

    success_count = 0
    errors = []

    # Caller-controlled association: authorize BEFORE storing anything.
    # Failures behave like any other upload validation error below.
    try:
        authorize_entity_attachment(current_user, entity_type, entity_id)
    except FileError as e:
        for f in uploaded_files:
            if f.filename:
                errors.append(f"{f.filename}: {e}")
        for err in errors:
            flash(err, "error")
        return _safe_back_redirect()

    for f in uploaded_files:
        if not f.filename:
            continue
        try:
            f.seek(0, 2)  # end
            file_size = f.tell()
            f.seek(0)

            upload_file(
                file_storage=f,
                filename=f.filename,
                file_size=file_size,
                content_type=f.content_type,
                category=category,
                uploader_user_id=current_user.id,
                entity_type=entity_type,
                entity_id=entity_id,
                visibility=visibility,
            )
            success_count += 1
        except FileError as e:
            errors.append(f"{f.filename}: {e}")

    if success_count > 0:
        flash(f"{success_count} file(s) uploaded successfully.", "success")
    if errors:
        for err in errors:
            flash(err, "error")

    # Redirect back to originating page
    return _safe_back_redirect()


# ---------------------------------------------------------------------------
# Download endpoint
# ---------------------------------------------------------------------------


@file_bp.route("/<int:file_id>/download")
@login_required
def download(file_id):
    """Download a file."""
    record = StoredFileModel.query.get(file_id)
    if record is None:
        abort(404)
    if record.status == "DELETED":
        abort(404)
    if not can_download_file(current_user, record):
        abort(403)

    try:
        _, stream = get_file_stream(file_id)
    except FileError:
        abort(404)

    return send_file(
        stream,
        mimetype=record.mime_type,
        download_name=record.original_filename,
        as_attachment=True,
    )


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


@file_bp.route("/api/<int:file_id>/metadata")
@login_required
def api_file_metadata(file_id):
    """Get file metadata as JSON."""
    record = StoredFileModel.query.get(file_id)
    if record is None:
        return jsonify({"error": "File not found."}), 404
    if not can_access_file(current_user, record):
        return jsonify({"error": "Access denied."}), 403

    return jsonify(get_file_metadata(file_id))


@file_bp.route("/api/<int:file_id>", methods=["DELETE"])
@login_required
def api_delete_file(file_id):
    """Delete a file via API."""
    record = StoredFileModel.query.get(file_id)
    if record is None:
        return jsonify({"error": "File not found."}), 404
    if not can_delete_file(current_user, record):
        return jsonify({"error": "Access denied."}), 403

    try:
        delete_file(file_id)
        return jsonify({"message": "File deleted."})
    except FileError as e:
        return jsonify({"error": str(e)}), 400
