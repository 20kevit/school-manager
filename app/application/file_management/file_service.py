"""File Management service — upload, download, delete, replace, metadata, authorization."""

from __future__ import annotations

import os
from datetime import datetime

from flask import current_app

from app.extensions import db
from app.infrastructure.database.models import (
    AcademyClassModel,
    ActivityModel,
    ActivitySubmissionModel,
    ParentProfileModel,
    StoredFileModel,
    StudentProfileModel,
    TeacherProfileModel,
)
from app.infrastructure.storage import (
    generate_storage_key,
    get_storage_backend,
)

# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------

#: Categories accepted on upload (admin UI list plus seed-time tuition docs).
ALLOWED_CATEGORIES = frozenset(
    {
        "PROFILE_PHOTO",
        "STUDENT_DOCUMENT",
        "ACTIVITY_ATTACHMENT",
        "ACTIVITY_SUBMISSION",
        "FINANCE_DOCUMENT",
        "EDUCATIONAL_MATERIAL",
        "TUITION",
        "OTHER",
    }
)

#: Visibility values accepted on upload.
ALLOWED_VISIBILITY = frozenset({"PRIVATE", "PUBLIC"})

#: Entity types the upload trust boundary understands. Anything else is
#: rejected at the route layer; the service stores only what callers pass
#: after route-level authorization (trusted server-side callers pass
#: pre-verified entities).
ATTACHABLE_ENTITY_TYPES = frozenset(
    {
        "",
        "activity_submission",
        "student_profile",
        "teacher_profile",
        "parent_profile",
    }
)


def _validate_category_visibility(category: str, visibility: str) -> None:
    if category not in ALLOWED_CATEGORIES:
        raise FileError(f"File category '{category}' is not supported.")
    if visibility not in ALLOWED_VISIBILITY:
        raise FileError(f"File visibility '{visibility}' is not supported.")


def authorize_entity_attachment(
    user, entity_type: str | None, entity_id: int | None
) -> None:
    """Verify the user may attach files to the given entity.

    Raises FileError (generic message, no existence oracle) when the entity
    type is unsupported, the entity does not exist, or the user has no
    relationship to it. Unattached uploads (empty type / null id) are
    uploader-scoped and always allowed here.
    """
    entity_type = entity_type or ""
    if not entity_type and entity_id is None:
        return
    if entity_type not in ATTACHABLE_ENTITY_TYPES:
        raise FileError("Attaching files to this item is not allowed.")
    if entity_id is None:
        raise FileError("Attaching files to this item is not allowed.")

    if user.has_role("ADMIN"):
        # Admins may attach anywhere, but the entity must still exist.
        if _find_attach_entity(entity_type, entity_id) is None:
            raise FileError("Attaching files to this item is not allowed.")
        return

    if entity_type == "activity_submission":
        submission = ActivitySubmissionModel.query.get(entity_id)
        if submission is None:
            raise FileError("Attaching files to this item is not allowed.")
        activity = ActivityModel.query.get(submission.activity_id)
        if activity is None:
            raise FileError("Attaching files to this item is not allowed.")
        if submission.student_user_id == user.id:
            return
        academy_class = (
            AcademyClassModel.query.get(activity.class_id)
            if activity.class_id
            else None
        )
        if academy_class is not None and academy_class.teacher_user_id == user.id:
            return
        raise FileError("Attaching files to this item is not allowed.")

    profile = _find_profile(entity_type, entity_id)
    if profile is None:
        raise FileError("Attaching files to this item is not allowed.")
    if profile.user_id == user.id:
        return
    raise FileError("Attaching files to this item is not allowed.")


def _find_attach_entity(entity_type: str, entity_id: int):
    if entity_type == "activity_submission":
        return ActivitySubmissionModel.query.get(entity_id)
    return _find_profile(entity_type, entity_id)


def _find_profile(entity_type: str, entity_id: int):
    if entity_type == "student_profile":
        return StudentProfileModel.query.get(entity_id)
    if entity_type == "teacher_profile":
        return TeacherProfileModel.query.get(entity_id)
    if entity_type == "parent_profile":
        return ParentProfileModel.query.get(entity_id)
    return None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class FileError(Exception):
    """Raised when a file operation fails."""


def validate_upload(
    filename: str,
    file_size: int,
    content_type: str | None,
    allowed_extensions: frozenset[str] | None = None,
    max_size: int | None = None,
) -> None:
    """Validate an uploaded file against size and type constraints."""
    if not filename:
        raise FileError("No filename provided.")

    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if not ext:
        raise FileError("File must have an extension.")

    allowed_exts = allowed_extensions or _get_allowed_extensions()
    if ext not in allowed_exts:
        raise FileError(
            f"File type '.{ext}' is not allowed. "
            f"Allowed: {', '.join(sorted(allowed_exts))}"
        )

    max_sz = max_size or _get_max_upload_size()
    if file_size > max_sz:
        max_mb = max_sz // (1024 * 1024)
        raise FileError(f"File size exceeds maximum of {max_mb} MB.")

    if file_size <= 0:
        raise FileError("File is empty.")

    if content_type:
        allowed_mimes = _get_allowed_mimetypes()
        if allowed_mimes and content_type not in allowed_mimes:
            raise FileError(f"File type '{content_type}' is not allowed.")


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe storage."""
    # Remove path components
    name = os.path.basename(filename)
    # Replace dangerous characters
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
    # Collapse multiple underscores
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("_.")


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


def upload_file(
    file_storage,
    filename: str,
    file_size: int,
    content_type: str | None,
    category: str = "OTHER",
    uploader_user_id: int | None = None,
    entity_type: str = "",
    entity_id: int | None = None,
    visibility: str = "PRIVATE",
    allowed_extensions: frozenset[str] | None = None,
    max_size: int | None = None,
) -> StoredFileModel:
    """Upload a file and create a metadata record.

    Args:
        file_storage: werkzeug FileStorage object
        filename: original filename
        file_size: size in bytes
        content_type: MIME type
        category: file category (PROFILE_PHOTO, STUDENT_DOCUMENT, etc.)
        uploader_user_id: ID of uploading user
        entity_type: associated entity type (e.g. "student", "activity")
        entity_id: associated entity ID
        visibility: PRIVATE or PUBLIC
        allowed_extensions: override default allowed extensions
        max_size: override default max size

    Returns:
        StoredFileModel record
    """
    validate_upload(filename, file_size, content_type, allowed_extensions, max_size)
    _validate_category_visibility(category, visibility)

    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    storage_key = generate_storage_key(category, ext)

    backend = get_storage_backend()
    actual_size = backend.save_stream(storage_key, file_storage)

    record = StoredFileModel(
        original_filename=sanitize_filename(filename),
        stored_filename=os.path.basename(storage_key),
        extension=ext,
        mime_type=content_type or "application/octet-stream",
        file_size=actual_size,
        storage_backend="local",
        storage_key=storage_key,
        status="ACTIVE",
        visibility=visibility,
        category=category,
        uploader_user_id=uploader_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.session.add(record)
    db.session.commit()
    return record


def upload_file_bytes(
    data: bytes,
    filename: str,
    content_type: str | None,
    category: str = "OTHER",
    uploader_user_id: int | None = None,
    entity_type: str = "",
    entity_id: int | None = None,
    visibility: str = "PRIVATE",
) -> StoredFileModel:
    """Upload raw bytes and create a metadata record."""
    # Same validation as the FileStorage path: extension allowlist, size
    # cap, and MIME allowlist (never trust client MIME alone — the
    # allowlist gates it).
    validate_upload(
        filename,
        len(data),
        content_type,
        allowed_extensions=None,
        max_size=None,
    )
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if not ext:
        raise FileError("File must have an extension.")
    _validate_category_visibility(category, visibility)
    storage_key = generate_storage_key(category, ext)

    backend = get_storage_backend()
    backend.save(storage_key, data)

    record = StoredFileModel(
        original_filename=sanitize_filename(filename),
        stored_filename=os.path.basename(storage_key),
        extension=ext,
        mime_type=content_type or "application/octet-stream",
        file_size=len(data),
        storage_backend="local",
        storage_key=storage_key,
        status="ACTIVE",
        visibility=visibility,
        category=category,
        uploader_user_id=uploader_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.session.add(record)
    db.session.commit()
    return record


# ---------------------------------------------------------------------------
# Download / Read
# ---------------------------------------------------------------------------


def get_file_record(file_id: int) -> StoredFileModel | None:
    """Get a file metadata record by ID."""
    return StoredFileModel.query.get(file_id)


def get_file_stream(file_id: int):
    """Get a file stream for download.

    Returns (record, file_stream) or raises FileError.
    """
    record = StoredFileModel.query.get(file_id)
    if record is None:
        raise FileError("File not found.")
    if record.status == "DELETED":
        raise FileError("File has been deleted.")

    backend = get_storage_backend()
    try:
        stream = backend.open(record.storage_key)
    except FileNotFoundError:
        raise FileError("File data not found in storage.")

    return record, stream


def get_file_metadata(file_id: int) -> dict:
    """Get file metadata as a dictionary."""
    record = StoredFileModel.query.get(file_id)
    if record is None:
        raise FileError("File not found.")
    return _record_to_dict(record)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def delete_file(file_id: int, physical: bool = False) -> bool:
    """Delete a file.

    Soft delete by default (marks status as DELETED).
    If physical=True, also removes the storage file.
    """
    record = StoredFileModel.query.get(file_id)
    if record is None:
        raise FileError("File not found.")
    if record.status == "DELETED":
        return True

    record.status = "DELETED"
    record.deleted_at = datetime.now()
    db.session.commit()

    if physical:
        backend = get_storage_backend()
        backend.delete(record.storage_key)

    return True


# ---------------------------------------------------------------------------
# Replace
# ---------------------------------------------------------------------------


def replace_file(
    file_id: int,
    file_storage,
    filename: str,
    file_size: int,
    content_type: str | None,
) -> StoredFileModel:
    """Replace a file's binary data while preserving metadata.

    The old storage file is deleted. Metadata is updated.
    """
    record = StoredFileModel.query.get(file_id)
    if record is None:
        raise FileError("File not found.")
    if record.status == "DELETED":
        raise FileError("Cannot replace a deleted file.")

    validate_upload(filename, file_size, content_type)

    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    new_storage_key = generate_storage_key(record.category, ext)

    backend = get_storage_backend()
    # Delete old file
    backend.delete(record.storage_key)
    # Save new file
    actual_size = backend.save_stream(new_storage_key, file_storage)

    record.original_filename = sanitize_filename(filename)
    record.stored_filename = os.path.basename(new_storage_key)
    record.extension = ext
    record.mime_type = content_type or "application/octet-stream"
    record.file_size = actual_size
    record.storage_key = new_storage_key
    record.updated_at = datetime.now()
    db.session.commit()
    return record


# ---------------------------------------------------------------------------
# Query / List
# ---------------------------------------------------------------------------


def list_files(
    category: str | None = None,
    status: str = "ACTIVE",
    uploader_user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[StoredFileModel], int]:
    """List files with optional filters. Returns (files, total_count)."""
    query = StoredFileModel.query

    if status:
        query = query.filter(StoredFileModel.status == status)
    if category:
        query = query.filter(StoredFileModel.category == category)
    if uploader_user_id:
        query = query.filter(StoredFileModel.uploader_user_id == uploader_user_id)
    if entity_type:
        query = query.filter(StoredFileModel.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(StoredFileModel.entity_id == entity_id)

    total = query.count()
    files = (
        query.order_by(StoredFileModel.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return files, total


def get_entity_files(entity_type: str, entity_id: int) -> list[StoredFileModel]:
    """Get all active files for a specific entity."""
    return (
        StoredFileModel.query.filter_by(
            entity_type=entity_type,
            entity_id=entity_id,
            status="ACTIVE",
        )
        .order_by(StoredFileModel.created_at)
        .all()
    )


def count_files(category: str | None = None, status: str = "ACTIVE") -> int:
    """Count files with optional filters."""
    query = StoredFileModel.query
    if status:
        query = query.filter(StoredFileModel.status == status)
    if category:
        query = query.filter(StoredFileModel.category == category)
    return query.count()


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def can_access_file(user, file_record: StoredFileModel) -> bool:
    """Check if a user can access a file.

    Rules:
    - Admin: always yes
    - Uploader: yes
    - PUBLIC files: yes (any authenticated user)
    - Entity-scoped readers: profile owners for *_profile entities;
      submission owners and class teachers for activity_submission entities
    - Unknown/unattached entities: uploader/admin/PUBLIC only
    """
    if user.has_role("ADMIN"):
        return True
    if file_record.uploader_user_id == user.id:
        return True
    if file_record.visibility == "PUBLIC":
        return True
    return _entity_read_allowed(user, file_record)


def _entity_read_allowed(user, file_record: StoredFileModel) -> bool:
    """Entity-scoped read access for PRIVATE files (additive only)."""
    entity_type = file_record.entity_type or ""
    entity_id = file_record.entity_id
    if not entity_type or entity_id is None:
        return False
    if entity_type == "activity_submission":
        submission = ActivitySubmissionModel.query.get(entity_id)
        if submission is None:
            return False
        if submission.student_user_id == user.id:
            return True
        activity = ActivityModel.query.get(submission.activity_id)
        if activity is None or not activity.class_id:
            return False
        academy_class = AcademyClassModel.query.get(activity.class_id)
        return academy_class is not None and academy_class.teacher_user_id == user.id
    profile = _find_profile(entity_type, entity_id)
    if profile is None:
        return False
    return profile.user_id == user.id


def can_download_file(user, file_record: StoredFileModel) -> bool:
    """Check if a user can download a file."""
    if file_record.status == "DELETED":
        return False
    return can_access_file(user, file_record)


def can_delete_file(user, file_record: StoredFileModel) -> bool:
    """Check if a user can delete a file."""
    if user.has_role("ADMIN"):
        return True
    if file_record.uploader_user_id == user.id:
        return True
    return False


# ---------------------------------------------------------------------------
# Orphan detection
# ---------------------------------------------------------------------------


def find_orphan_files() -> list[StoredFileModel]:
    """Find files with no entity association or missing storage."""
    backend = get_storage_backend()
    orphans = []

    records = StoredFileModel.query.filter_by(status="ACTIVE").all()
    for record in records:
        # No entity association
        if not record.entity_type or record.entity_id is None:
            orphans.append(record)
            continue
        # Storage file missing
        if not backend.exists(record.storage_key):
            orphans.append(record)

    return orphans


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _record_to_dict(record: StoredFileModel) -> dict:
    return {
        "id": record.id,
        "original_filename": record.original_filename,
        "stored_filename": record.stored_filename,
        "extension": record.extension,
        "mime_type": record.mime_type,
        "file_size": record.file_size,
        "storage_backend": record.storage_backend,
        "status": record.status,
        "visibility": record.visibility,
        "category": record.category,
        "uploader_user_id": record.uploader_user_id,
        "entity_type": record.entity_type,
        "entity_id": record.entity_id,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "deleted_at": record.deleted_at.isoformat() if record.deleted_at else None,
    }


def _get_allowed_extensions() -> frozenset[str]:
    return current_app.config.get("FILE_ALLOWED_EXTENSIONS", ALLOWED_EXTENSIONS_DEFAULT)


def _get_max_upload_size() -> int:
    return current_app.config.get("FILE_MAX_UPLOAD_SIZE", MAX_SIZE_DEFAULT)


def _get_allowed_mimetypes() -> frozenset[str]:
    return current_app.config.get("FILE_ALLOWED_MIMETYPES", MIMETYPES_DEFAULT)


ALLOWED_EXTENSIONS_DEFAULT = frozenset(
    {"jpg", "jpeg", "png", "webp", "pdf", "txt", "csv"}
)
MAX_SIZE_DEFAULT = 5 * 1024 * 1024
MIMETYPES_DEFAULT = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
        "text/plain",
        "text/csv",
    }
)
