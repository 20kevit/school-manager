"""File Management domain entities."""

from __future__ import annotations

import enum


class FileStatus(enum.StrEnum):
    """Lifecycle status of a stored file."""

    ACTIVE = "ACTIVE"
    DELETED = "DELETED"


class FileVisibility(enum.StrEnum):
    """Visibility level of a stored file."""

    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"


class FileCategory(enum.StrEnum):
    """Category of a stored file for classification."""

    PROFILE_PHOTO = "PROFILE_PHOTO"
    STUDENT_DOCUMENT = "STUDENT_DOCUMENT"
    ACTIVITY_ATTACHMENT = "ACTIVITY_ATTACHMENT"
    ACTIVITY_SUBMISSION = "ACTIVITY_SUBMISSION"
    FINANCE_DOCUMENT = "FINANCE_DOCUMENT"
    EDUCATIONAL_MATERIAL = "EDUCATIONAL_MATERIAL"
    OTHER = "OTHER"


# Default allowed extensions
DEFAULT_ALLOWED_EXTENSIONS = frozenset(
    {"jpg", "jpeg", "png", "webp", "pdf", "txt", "csv"}
)

# Default max upload size: 5 MB
DEFAULT_MAX_UPLOAD_SIZE = 5 * 1024 * 1024


class StoredFile:
    """Domain entity representing a file stored in the system.

    This is a pure domain object with no infrastructure dependencies.
    """

    def __init__(
        self,
        id: int | None = None,
        original_filename: str = "",
        stored_filename: str = "",
        extension: str = "",
        mime_type: str = "",
        file_size: int = 0,
        storage_backend: str = "local",
        storage_key: str = "",
        status: FileStatus = FileStatus.ACTIVE,
        visibility: FileVisibility = FileVisibility.PRIVATE,
        category: FileCategory = FileCategory.OTHER,
        uploader_user_id: int | None = None,
        created_at: None = None,
        updated_at: None = None,
        deleted_at: None = None,
        # Association fields
        entity_type: str = "",
        entity_id: int | None = None,
    ):
        self.id = id
        self.original_filename = original_filename
        self.stored_filename = stored_filename
        self.extension = extension
        self.mime_type = mime_type
        self.file_size = file_size
        self.storage_backend = storage_backend
        self.storage_key = storage_key
        self.status = status
        self.visibility = visibility
        self.category = category
        self.uploader_user_id = uploader_user_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.deleted_at = deleted_at
        self.entity_type = entity_type
        self.entity_id = entity_id

    @property
    def is_active(self) -> bool:
        return self.status == FileStatus.ACTIVE

    @property
    def is_deleted(self) -> bool:
        return self.status == FileStatus.DELETED

    @property
    def is_public(self) -> bool:
        return self.visibility == FileVisibility.PUBLIC

    @property
    def is_private(self) -> bool:
        return self.visibility == FileVisibility.PRIVATE

    @property
    def display_size(self) -> str:
        """Human-readable file size."""
        size = self.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    def __repr__(self) -> str:
        return (
            f"<StoredFile id={self.id} "
            f"original={self.original_filename!r} "
            f"category={self.category.value}>"
        )
