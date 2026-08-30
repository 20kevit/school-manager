# ADR-006: File Storage Architecture

## Status

Accepted

## Context

The Academy Management System needs to handle file uploads across multiple modules:
- Student profile photos
- Activity attachments and submissions
- Finance documents/receipts
- Educational materials

Prior to P11, file handling was activity-specific (`ActivityFileModel` with direct filesystem operations in `activity_service.py`). There was no centralized file management, no storage abstraction, and no way for other modules to use file upload without duplicating logic.

## Decision

### Storage Abstraction

Create a `StorageBackend` abstract base class in the infrastructure layer. Application and domain code depend on this abstraction, never on `os` or `pathlib` directly.

Implement `LocalStorageBackend` as the only concrete backend in P11. Future S3/object storage can be added by implementing a new backend without changing application code.

### Association Strategy

Use generic `entity_type` (string) + `entity_id` (integer) fields on a single `stored_files` table rather than:
- Separate file tables per module (would duplicate schema and logic)
- Polymorphic ORM inheritance (would add complexity)
- Generic foreign keys (would add SQLAlchemy complexity)

The string-based entity_type allows new associations without migrations.

### File Status

Use soft deletion (status = DELETED) by default. Physical file cleanup is optional and can be done via orphan detection. This preserves metadata history and prevents accidental data loss.

### File Naming

Generate UUID-based storage keys in a date-organized directory structure:
```
files/YYYY/MM/<uuid>.<ext>
```

This prevents:
- Path traversal attacks
- Filename collisions
- Information leakage through filenames

### Validation

Centralized validation in `file_service.py`:
- Extension allowlist (configurable per category)
- MIME type validation (server-side)
- Configurable size limits (default 5 MB)
- Empty file rejection

### Authorization

Three-tier authorization:
1. Admin: full access to all files
2. Owner (uploader): access to own files
3. Public files: accessible to all authenticated users

Entity-specific authorization (e.g., teacher accessing class files) is checked at the caller level, not in the file service.

## Consequences

### Positive
- Single file management module serves all current and future features
- Storage backend can be replaced without changing application code
- No schema migrations needed for new file categories
- Soft deletion preserves audit trail
- Secure by default (private visibility, UUID naming, path traversal prevention)

### Negative
- Generic association means no foreign key constraints between file records and entities
- Orphan files require periodic detection (no automated cleanup in P11)
- Existing `ActivityFileModel` is preserved for backward compatibility (will coexist until migration)

### Future Considerations
- S3/object storage backend implementation
- Automated orphan cleanup via background jobs
- Thumbnail generation for image files
- File versioning (currently handled by activity submission versioning)
