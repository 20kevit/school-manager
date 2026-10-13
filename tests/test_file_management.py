"""Tests for P11 — File & Document Management."""

from __future__ import annotations

import io
import tempfile
from unittest.mock import MagicMock

import pytest

from app import create_app
from app.application.file_management.file_service import (
    FileError,
    can_access_file,
    can_delete_file,
    can_download_file,
    count_files,
    delete_file,
    find_orphan_files,
    get_entity_files,
    get_file_metadata,
    get_file_stream,
    list_files,
    replace_file,
    sanitize_filename,
    upload_file,
    upload_file_bytes,
    validate_upload,
)
from app.extensions import db as _db
from app.infrastructure.database.models import (
    ActivityFileModel,
    RoleModel,
    StoredFileModel,
    StudentProfileModel,
    UserModel,
)
from app.infrastructure.storage import (
    LocalStorageBackend,
    generate_storage_key,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def app():
    app = create_app("testing")
    return app


@pytest.fixture(scope="function")
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app, db):
    return app.test_client()


@pytest.fixture
def admin_user(db):
    user = UserModel(login="admin_file")
    user.set_password("pass123")
    role = RoleModel(name="ADMIN")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def student_user(db):
    from datetime import date

    user = UserModel(login="student_file")
    user.set_password("pass123")
    role = RoleModel(name="STUDENT")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.flush()
    profile = StudentProfileModel(
        user_id=user.id,
        first_name="Ali",
        last_name="Test",
        national_id="9998887777",
        mobile_phone="09120001122",
        birth_date=date(2001, 5, 10),
        gender="MALE",
    )
    db.session.add(profile)
    db.session.commit()
    return user


@pytest.fixture
def teacher_user(db):
    user = UserModel(login="teacher_file")
    user.set_password("pass123")
    role = RoleModel(name="TEACHER")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def storage_dir(app):
    d = tempfile.mkdtemp()
    yield d
    import shutil

    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def storage_backend(storage_dir):
    return LocalStorageBackend(storage_dir)


# ---------------------------------------------------------------------------
# Domain entity tests
# ---------------------------------------------------------------------------


class TestStoredFileDomain:
    """Test domain entity."""

    def test_stored_file_defaults(self):
        from app.domain.file_management.entities import (
            FileCategory,
            FileStatus,
            FileVisibility,
            StoredFile,
        )

        f = StoredFile()
        assert f.status == FileStatus.ACTIVE
        assert f.visibility == FileVisibility.PRIVATE
        assert f.category == FileCategory.OTHER
        assert f.is_active is True
        assert f.is_deleted is False
        assert f.is_private is True
        assert f.is_public is False

    def test_stored_file_properties(self):
        from app.domain.file_management.entities import (
            FileStatus,
            FileVisibility,
            StoredFile,
        )

        f = StoredFile(status=FileStatus.DELETED, visibility=FileVisibility.PUBLIC)
        assert f.is_active is False
        assert f.is_deleted is True
        assert f.is_public is True
        assert f.is_private is False

    def test_display_size_bytes(self):
        from app.domain.file_management.entities import StoredFile

        f = StoredFile(file_size=512)
        assert f.display_size == "512 B"

    def test_display_size_kb(self):
        from app.domain.file_management.entities import StoredFile

        f = StoredFile(file_size=2048)
        assert "KB" in f.display_size

    def test_display_size_mb(self):
        from app.domain.file_management.entities import StoredFile

        f = StoredFile(file_size=2 * 1024 * 1024)
        assert "MB" in f.display_size

    def test_repr(self):
        from app.domain.file_management.entities import StoredFile

        f = StoredFile(id=1, original_filename="test.pdf")
        assert "test.pdf" in repr(f)


class TestFileEnums:
    """Test file status, visibility, and category enums."""

    def test_file_status_values(self):
        from app.domain.file_management.entities import FileStatus

        assert FileStatus.ACTIVE.value == "ACTIVE"
        assert FileStatus.DELETED.value == "DELETED"

    def test_file_visibility_values(self):
        from app.domain.file_management.entities import FileVisibility

        assert FileVisibility.PRIVATE.value == "PRIVATE"
        assert FileVisibility.PUBLIC.value == "PUBLIC"

    def test_file_category_values(self):
        from app.domain.file_management.entities import FileCategory

        assert FileCategory.PROFILE_PHOTO.value == "PROFILE_PHOTO"
        assert FileCategory.STUDENT_DOCUMENT.value == "STUDENT_DOCUMENT"
        assert FileCategory.ACTIVITY_ATTACHMENT.value == "ACTIVITY_ATTACHMENT"
        assert FileCategory.ACTIVITY_SUBMISSION.value == "ACTIVITY_SUBMISSION"
        assert FileCategory.FINANCE_DOCUMENT.value == "FINANCE_DOCUMENT"
        assert FileCategory.EDUCATIONAL_MATERIAL.value == "EDUCATIONAL_MATERIAL"
        assert FileCategory.OTHER.value == "OTHER"


# ---------------------------------------------------------------------------
# Storage tests
# ---------------------------------------------------------------------------


class TestLocalStorageBackend:
    """Test local storage backend."""

    def test_save_and_open(self, storage_backend):
        storage_backend.save("test/file.txt", b"hello world")
        with storage_backend.open("test/file.txt") as f:
            assert f.read() == b"hello world"

    def test_save_stream(self, storage_backend):
        stream = io.BytesIO(b"stream data")
        size = storage_backend.save_stream("test/stream.bin", stream)
        assert size == 11
        with storage_backend.open("test/stream.bin") as f:
            assert f.read() == b"stream data"

    def test_exists(self, storage_backend):
        assert not storage_backend.exists("test/missing.txt")
        storage_backend.save("test/exists.txt", b"data")
        assert storage_backend.exists("test/exists.txt")

    def test_delete(self, storage_backend):
        storage_backend.save("test/todel.txt", b"data")
        assert storage_backend.delete("test/todel.txt") is True
        assert not storage_backend.exists("test/todel.txt")
        assert storage_backend.delete("test/todel.txt") is False

    def test_replace(self, storage_backend):
        storage_backend.save("test/rep.txt", b"old")
        storage_backend.replace("test/rep.txt", b"new")
        with storage_backend.open("test/rep.txt") as f:
            assert f.read() == b"new"

    def test_get_size(self, storage_backend):
        storage_backend.save("test/sized.txt", b"12345")
        assert storage_backend.get_size("test/sized.txt") == 5

    def test_open_missing_file(self, storage_backend):
        with pytest.raises(FileNotFoundError):
            storage_backend.open("test/nope.txt")

    def test_path_traversal_blocked(self, storage_backend):
        with pytest.raises(ValueError, match="Path traversal"):
            storage_backend.save("../../../etc/passwd", b"evil")

    def test_path_traversal_open(self, storage_backend):
        with pytest.raises(ValueError, match="Path traversal"):
            storage_backend.open("../../etc/passwd")


class TestGenerateStorageKey:
    """Test storage key generation."""

    def test_key_format(self):
        key = generate_storage_key("OTHER", "pdf")
        assert key.startswith("files/")
        assert key.endswith(".pdf")

    def test_key_unique(self):
        key1 = generate_storage_key("OTHER", "txt")
        key2 = generate_storage_key("OTHER", "txt")
        assert key1 != key2

    def test_key_strips_dot(self):
        key = generate_storage_key("OTHER", ".jpg")
        assert not key.endswith("..jpg")


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestValidation:
    """Test file validation."""

    def test_valid_upload(self, app):
        with app.app_context():
            validate_upload("test.pdf", 1024, "application/pdf")

    def test_empty_filename(self, app):
        with app.app_context():
            with pytest.raises(FileError, match="No filename"):
                validate_upload("", 1024, "application/pdf")

    def test_no_extension(self, app):
        with app.app_context():
            with pytest.raises(FileError, match="extension"):
                validate_upload("noext", 1024, "text/plain")

    def test_invalid_extension(self, app):
        with app.app_context():
            with pytest.raises(FileError, match="not allowed"):
                validate_upload("evil.exe", 1024, "application/octet-stream")

    def test_oversized_file(self, app):
        with app.app_context():
            with pytest.raises(FileError, match="exceeds maximum"):
                validate_upload("big.pdf", 10 * 1024 * 1024, "application/pdf")

    def test_empty_file(self, app):
        with app.app_context():
            with pytest.raises(FileError, match="empty"):
                validate_upload("empty.pdf", 0, "application/pdf")

    def test_invalid_mimetype(self, app):
        with app.app_context():
            with pytest.raises(FileError, match="not allowed"):
                validate_upload("test.pdf", 1024, "application/x-executable")

    def test_custom_extensions(self, app):
        with app.app_context():
            validate_upload(
                "test.docx",
                1024,
                None,
                allowed_extensions=frozenset({"docx"}),
            )

    def test_custom_max_size(self, app):
        with app.app_context():
            with pytest.raises(FileError, match="exceeds maximum"):
                validate_upload("test.pdf", 200, "application/pdf", max_size=100)


class TestSanitizeFilename:
    """Test filename sanitization."""

    def test_normal_name(self):
        assert sanitize_filename("document.pdf") == "document.pdf"

    def test_path_traversal(self):
        result = sanitize_filename("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_dangerous_chars(self):
        result = sanitize_filename("file name (1).pdf")
        assert "(" not in result
        assert ")" not in result

    def test_multiple_underscores(self):
        result = sanitize_filename("a___b.pdf")
        assert "___" not in result


# ---------------------------------------------------------------------------
# Upload tests
# ---------------------------------------------------------------------------


class TestUpload:
    """Test file upload."""

    def _make_file_storage(self, content=b"test content", filename="test.pdf"):
        fs = MagicMock()
        fs.filename = filename
        fs.content_type = "application/pdf"
        fs.read = MagicMock(side_effect=[content, b""])
        fs.seek = MagicMock()
        fs.tell = MagicMock(return_value=len(content))
        return fs

    def test_upload_basic(self, app, db):
        with app.app_context():
            fs = self._make_file_storage(b"hello", "hello.pdf")
            record = upload_file(
                file_storage=fs,
                filename="hello.pdf",
                file_size=5,
                content_type="application/pdf",
                category="OTHER",
                uploader_user_id=None,
            )
            assert record.id is not None
            assert record.original_filename == "hello.pdf"
            assert record.extension == "pdf"
            assert record.status == "ACTIVE"
            assert record.visibility == "PRIVATE"

    def test_upload_with_entity(self, app, db):
        with app.app_context():
            fs = self._make_file_storage(b"data", "doc.pdf")
            record = upload_file(
                file_storage=fs,
                filename="doc.pdf",
                file_size=4,
                content_type="application/pdf",
                category="STUDENT_DOCUMENT",
                entity_type="student",
                entity_id=1,
            )
            assert record.entity_type == "student"
            assert record.entity_id == 1
            assert record.category == "STUDENT_DOCUMENT"

    def test_upload_invalid_file(self, app, db):
        with app.app_context():
            fs = self._make_file_storage(b"data", "evil.exe")
            with pytest.raises(FileError, match="not allowed"):
                upload_file(
                    file_storage=fs,
                    filename="evil.exe",
                    file_size=4,
                    content_type="application/octet-stream",
                )

    def test_upload_bytes(self, app, db):
        with app.app_context():
            record = upload_file_bytes(
                data=b"raw bytes",
                filename="raw.txt",
                content_type="text/plain",
                category="OTHER",
            )
            assert record.id is not None
            assert record.file_size == 9


# ---------------------------------------------------------------------------
# Download tests
# ---------------------------------------------------------------------------


class TestDownload:
    """Test file download."""

    def test_get_file_stream(self, app, db):
        with app.app_context():
            record = upload_file_bytes(b"content", "f.txt", "text/plain")
            rec, stream = get_file_stream(record.id)
            assert rec.id == record.id
            stream.close()

    def test_get_stream_deleted_file(self, app, db):
        with app.app_context():
            record = upload_file_bytes(b"content", "f.txt", "text/plain")
            delete_file(record.id)
            with pytest.raises(FileError, match="deleted"):
                get_file_stream(record.id)

    def test_get_stream_nonexistent(self, app, db):
        with app.app_context():
            with pytest.raises(FileError, match="not found"):
                get_file_stream(99999)

    def test_get_file_metadata(self, app, db):
        with app.app_context():
            record = upload_file_bytes(b"meta", "meta.pdf", "application/pdf")
            meta = get_file_metadata(record.id)
            assert meta["original_filename"] == "meta.pdf"
            assert meta["extension"] == "pdf"
            assert meta["status"] == "ACTIVE"


# ---------------------------------------------------------------------------
# Delete tests
# ---------------------------------------------------------------------------


class TestDelete:
    """Test file deletion."""

    def test_soft_delete(self, app, db):
        with app.app_context():
            record = upload_file_bytes(b"data", "del.txt", "text/plain")
            assert record.status == "ACTIVE"
            delete_file(record.id)
            refreshed = StoredFileModel.query.get(record.id)
            assert refreshed.status == "DELETED"
            assert refreshed.deleted_at is not None

    def test_delete_nonexistent(self, app, db):
        with app.app_context():
            with pytest.raises(FileError, match="not found"):
                delete_file(99999)

    def test_double_delete(self, app, db):
        with app.app_context():
            record = upload_file_bytes(b"data", "del.txt", "text/plain")
            delete_file(record.id)
            result = delete_file(record.id)
            assert result is True


# ---------------------------------------------------------------------------
# Replace tests
# ---------------------------------------------------------------------------


class TestReplace:
    """Test file replacement."""

    def test_replace_file(self, app, db):
        with app.app_context():
            record = upload_file_bytes(b"old data", "rep.txt", "text/plain")
            old_key = record.storage_key

            new_fs = MagicMock()
            new_fs.read = MagicMock(side_effect=[b"new data", b""])
            new_fs.seek = MagicMock()
            new_fs.tell = MagicMock(return_value=8)

            replaced = replace_file(record.id, new_fs, "new.txt", 8, "text/plain")
            assert replaced.original_filename == "new.txt"
            assert replaced.extension == "txt"
            assert replaced.id == record.id
            assert replaced.storage_key != old_key

    def test_replace_deleted_file(self, app, db):
        with app.app_context():
            record = upload_file_bytes(b"data", "f.txt", "text/plain")
            delete_file(record.id)
            new_fs = MagicMock()
            new_fs.read = MagicMock(side_effect=[b"x", b""])
            new_fs.seek = MagicMock()
            new_fs.tell = MagicMock(return_value=1)
            with pytest.raises(FileError, match="deleted"):
                replace_file(record.id, new_fs, "x.txt", 1, "text/plain")


# ---------------------------------------------------------------------------
# List / Query tests
# ---------------------------------------------------------------------------


class TestListFiles:
    """Test file listing."""

    def test_list_all(self, app, db):
        with app.app_context():
            upload_file_bytes(b"a", "a.txt", "text/plain")
            upload_file_bytes(b"b", "b.pdf", "application/pdf")
            files, total = list_files()
            assert total == 2

    def test_list_by_category(self, app, db):
        with app.app_context():
            upload_file_bytes(b"a", "a.txt", "text/plain", category="OTHER")
            upload_file_bytes(
                b"b", "b.pdf", "application/pdf", category="STUDENT_DOCUMENT"
            )
            files, total = list_files(category="STUDENT_DOCUMENT")
            assert total == 1
            assert files[0].category == "STUDENT_DOCUMENT"

    def test_list_by_status(self, app, db):
        with app.app_context():
            r1 = upload_file_bytes(b"a", "a.txt", "text/plain")
            upload_file_bytes(b"b", "b.txt", "text/plain")
            delete_file(r1.id)
            files, total = list_files(status="ACTIVE")
            assert total == 1
            files_deleted, total_d = list_files(status="DELETED")
            assert total_d == 1

    def test_list_pagination(self, app, db):
        with app.app_context():
            for i in range(5):
                upload_file_bytes(f"data{i}".encode(), f"f{i}.txt", "text/plain")
            files, total = list_files(page=1, per_page=2)
            assert len(files) == 2
            assert total == 5

    def test_count_files(self, app, db):
        with app.app_context():
            upload_file_bytes(b"a", "a.txt", "text/plain")
            upload_file_bytes(b"b", "b.txt", "text/plain")
            assert count_files() == 2
            assert count_files(category="OTHER") == 2

    def test_get_entity_files(self, app, db):
        with app.app_context():
            upload_file_bytes(
                b"a", "a.txt", "text/plain", entity_type="student", entity_id=1
            )
            upload_file_bytes(
                b"b", "b.txt", "text/plain", entity_type="student", entity_id=1
            )
            upload_file_bytes(
                b"c", "c.txt", "text/plain", entity_type="student", entity_id=2
            )
            files = get_entity_files("student", 1)
            assert len(files) == 2


# ---------------------------------------------------------------------------
# Authorization tests
# ---------------------------------------------------------------------------


class TestAuthorization:
    """Test file authorization."""

    def test_admin_can_access_any(self, app, db, admin_user):
        with app.app_context():
            record = upload_file_bytes(
                b"data", "f.txt", "text/plain", uploader_user_id=None
            )
            assert can_access_file(admin_user, record) is True

    def test_uploader_can_access(self, app, db, student_user):
        with app.app_context():
            record = upload_file_bytes(
                b"data", "f.txt", "text/plain", uploader_user_id=student_user.id
            )
            assert can_access_file(student_user, record) is True

    def test_public_file_accessible(self, app, db, student_user, teacher_user):
        with app.app_context():
            record = upload_file_bytes(
                b"data", "f.txt", "text/plain", visibility="PUBLIC"
            )
            assert can_access_file(teacher_user, record) is True

    def test_private_file_not_accessible(self, app, db, student_user, teacher_user):
        with app.app_context():
            record = upload_file_bytes(
                b"data",
                "f.txt",
                "text/plain",
                uploader_user_id=student_user.id,
                visibility="PRIVATE",
            )
            assert can_access_file(teacher_user, record) is False

    def test_admin_can_delete(self, app, db, admin_user):
        with app.app_context():
            record = upload_file_bytes(b"data", "f.txt", "text/plain")
            assert can_delete_file(admin_user, record) is True

    def test_non_owner_cannot_delete(self, app, db, student_user, teacher_user):
        with app.app_context():
            record = upload_file_bytes(
                b"data",
                "f.txt",
                "text/plain",
                uploader_user_id=student_user.id,
            )
            assert can_delete_file(teacher_user, record) is False

    def test_cannot_download_deleted(self, app, db, admin_user):
        with app.app_context():
            record = upload_file_bytes(b"data", "f.txt", "text/plain")
            delete_file(record.id)
            assert can_download_file(admin_user, record) is False


# ---------------------------------------------------------------------------
# Orphan detection tests
# ---------------------------------------------------------------------------


class TestOrphanDetection:
    """Test orphan file detection."""

    def test_no_orphans_initially(self, app, db):
        with app.app_context():
            orphans = find_orphan_files()
            assert len(orphans) == 0

    def test_orphan_no_entity(self, app, db):
        with app.app_context():
            upload_file_bytes(
                b"data", "f.txt", "text/plain", entity_type="", entity_id=None
            )
            orphans = find_orphan_files()
            assert len(orphans) == 1

    def test_non_orphan_with_entity(self, app, db):
        with app.app_context():
            upload_file_bytes(
                b"data", "f.txt", "text/plain", entity_type="student", entity_id=1
            )
            orphans = find_orphan_files()
            assert len(orphans) == 0


# ---------------------------------------------------------------------------
# Admin route tests
# ---------------------------------------------------------------------------


class TestAdminRoutes:
    """Test admin file management routes."""

    def test_admin_file_list(self, client, admin_user):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)
        resp = client.get("/files/admin")
        assert resp.status_code == 200

    def test_admin_file_detail(self, client, admin_user, app, db):
        with app.app_context():
            record = upload_file_bytes(b"data", "detail.pdf", "application/pdf")
            file_id = record.id
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)
        resp = client.get(f"/files/admin/{file_id}")
        assert resp.status_code == 200

    def test_admin_orphans(self, client, admin_user):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)
        resp = client.get("/files/admin/orphans")
        assert resp.status_code == 200

    def test_unauthenticated_redirected(self, client):
        resp = client.get("/files/admin")
        assert resp.status_code == 302


# ---------------------------------------------------------------------------
# Upload/Download route tests
# ---------------------------------------------------------------------------


class TestUploadDownloadRoutes:
    """Test upload and download routes."""

    def test_upload_via_form(self, client, student_user, app):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(student_user.id)
        data = {
            "files": (io.BytesIO(b"test content"), "upload_test.pdf"),
            "category": "OTHER",
        }
        resp = client.post(
            "/files/upload",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_download_file(self, client, student_user, app, db):
        with app.app_context():
            record = upload_file_bytes(
                b"download me",
                "dl.txt",
                "text/plain",
                uploader_user_id=student_user.id,
            )
            file_id = record.id
        with client.session_transaction() as sess:
            sess["_user_id"] = str(student_user.id)
        resp = client.get(f"/files/{file_id}/download")
        assert resp.status_code == 200

    def test_download_deleted_404(self, client, student_user, app, db):
        with app.app_context():
            record = upload_file_bytes(b"data", "f.txt", "text/plain")
            delete_file(record.id)
            file_id = record.id
        with client.session_transaction() as sess:
            sess["_user_id"] = str(student_user.id)
        resp = client.get(f"/files/{file_id}/download")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


class TestAPI:
    """Test API endpoints."""

    def test_metadata_api(self, client, admin_user, app, db):
        with app.app_context():
            record = upload_file_bytes(b"data", "api.pdf", "application/pdf")
            file_id = record.id
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)
        resp = client.get(f"/files/api/{file_id}/metadata")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["original_filename"] == "api.pdf"

    def test_metadata_nonexistent(self, client, admin_user):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)
        resp = client.get("/files/api/99999/metadata")
        assert resp.status_code == 404

    def test_delete_api(self, client, admin_user, app, db):
        with app.app_context():
            record = upload_file_bytes(b"data", "del_api.txt", "text/plain")
            file_id = record.id
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)
        resp = client.delete(f"/files/api/{file_id}")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Security tests
# ---------------------------------------------------------------------------


class TestSecurity:
    """Test security aspects."""

    def test_path_traversal_in_storage(self, storage_dir):
        backend = LocalStorageBackend(storage_dir)
        with pytest.raises(ValueError, match="Path traversal"):
            backend.save("../../../etc/secret", b"evil")

    def test_private_file_not_publicly_accessible(
        self, app, db, student_user, teacher_user
    ):
        with app.app_context():
            record = upload_file_bytes(
                b"secret",
                "secret.pdf",
                "application/pdf",
                uploader_user_id=student_user.id,
                visibility="PRIVATE",
            )
            assert can_access_file(teacher_user, record) is False

    def test_deleted_file_not_downloadable(self, app, db, admin_user):
        with app.app_context():
            record = upload_file_bytes(b"data", "f.txt", "text/plain")
            delete_file(record.id)
            assert can_download_file(admin_user, record) is False

    def test_cross_student_no_access(self, app, db, student_user, teacher_user):
        with app.app_context():
            # Student A uploads private file
            record = upload_file_bytes(
                b"data",
                "private.txt",
                "text/plain",
                uploader_user_id=student_user.id,
                visibility="PRIVATE",
            )
            # Teacher (not owner, not admin) cannot access
            assert can_access_file(teacher_user, record) is False

    def test_uploaded_files_persist_in_db(self, app, db):
        with app.app_context():
            record = upload_file_bytes(b"persist", "persist.txt", "text/plain")
            found = StoredFileModel.query.get(record.id)
            assert found is not None
            assert found.original_filename == "persist.txt"
            assert found.stored_filename != "persist.txt"


# ---------------------------------------------------------------------------
# Integration with existing models
# ---------------------------------------------------------------------------


class TestExistingActivityFilesPreserved:
    """Ensure existing ActivityFileModel still works."""

    def test_activity_file_model_exists(self, db):
        assert ActivityFileModel is not None
        assert hasattr(ActivityFileModel, "submission_id")
        assert hasattr(ActivityFileModel, "filename")
        assert hasattr(ActivityFileModel, "original_filename")

    def test_stored_file_model_exists(self, db):
        assert StoredFileModel is not None
        assert hasattr(StoredFileModel, "storage_key")
        assert hasattr(StoredFileModel, "category")
        assert hasattr(StoredFileModel, "entity_type")


# ---------------------------------------------------------------------------
# Upload trust-boundary authorization (regression coverage)
# ---------------------------------------------------------------------------


class TestUploadAuthorization:
    """Caller-controlled entity_type/entity_id/visibility must be authorized."""

    def _login_session(self, client, user):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

    def _file_storage(self, content=b"x" * 10, filename="ok.pdf"):
        fs = MagicMock()
        fs.filename = filename
        fs.content_type = "application/pdf"
        fs.read = MagicMock(side_effect=[content, b""])
        fs.seek = MagicMock()
        fs.tell = MagicMock(return_value=len(content))
        return fs

    def _other_student(self, db):
        from datetime import date

        from app.infrastructure.database.models import StudentProfileModel

        user = UserModel(login="victim_student")
        user.set_password("pass123")
        role = RoleModel.query.get("STUDENT")
        if role is None:
            role = RoleModel(name="STUDENT")
            db.session.add(role)
            db.session.flush()
        user.roles.append(role)
        db.session.add(user)
        db.session.flush()
        db.session.add(
            StudentProfileModel(
                user_id=user.id,
                first_name="Victim",
                last_name="Student",
                national_id="1112223334",
                mobile_phone="09120009999",
                birth_date=date(2002, 3, 3),
                gender="FEMALE",
            )
        )
        db.session.commit()
        return user

    def _submission_setup(self, db, student_user, teacher_user):
        from datetime import date

        from app.infrastructure.database.models import (
            AcademyClassModel,
            ActivityModel,
            ActivitySubmissionModel,
            CourseModel,
            EnrollmentModel,
        )

        course = CourseModel(title="C", description="d", num_sessions=4)
        db.session.add(course)
        db.session.flush()
        cls = AcademyClassModel(
            course_id=course.id,
            title="K",
            start_date=date(2026, 1, 1),
            capacity=10,
            num_sessions=4,
            status="ACTIVE",
            teacher_user_id=teacher_user.id,
        )
        db.session.add(cls)
        db.session.flush()
        enrollment = EnrollmentModel(
            student_user_id=student_user.id, class_id=cls.id, status="APPROVED"
        )
        db.session.add(enrollment)
        db.session.flush()
        activity = ActivityModel(type="HOMEWORK", title="HW", class_id=cls.id)
        db.session.add(activity)
        db.session.flush()
        submission = ActivitySubmissionModel(
            activity_id=activity.id,
            student_user_id=student_user.id,
            enrollment_id=enrollment.id,
        )
        db.session.add(submission)
        db.session.commit()
        return submission

    # -- service-side validation -----------------------------------------

    def test_upload_rejects_unknown_category(self, app, db):
        from app.application.file_management.file_service import upload_file

        with app.app_context():
            with pytest.raises(FileError, match="not supported"):
                upload_file(
                    file_storage=self._file_storage(),
                    filename="ok.pdf",
                    file_size=10,
                    content_type="application/pdf",
                    category="NOPE",
                )

    def test_upload_rejects_unknown_visibility(self, app, db):
        from app.application.file_management.file_service import upload_file

        with app.app_context():
            with pytest.raises(FileError, match="not supported"):
                upload_file(
                    file_storage=self._file_storage(),
                    filename="ok.pdf",
                    file_size=10,
                    content_type="application/pdf",
                    visibility="SUPER_SECRET",
                )

    def test_upload_sanitizes_original_filename(self, app, db):
        from app.application.file_management.file_service import upload_file

        with app.app_context():
            record = upload_file(
                file_storage=self._file_storage(filename="../../evil.pdf"),
                filename="../../evil.pdf",
                file_size=10,
                content_type="application/pdf",
            )
            assert "/" not in record.original_filename
            assert ".." not in record.original_filename

    # -- entity attachment authorization ----------------------------------

    def test_forged_profile_attachment_rejected(self, app, db, student_user):
        from app.application.file_management.file_service import (
            authorize_entity_attachment,
        )

        victim = self._other_student(db)
        profile_id = victim.student_profile.id
        with app.app_context():
            with pytest.raises(FileError):
                authorize_entity_attachment(student_user, "student_profile", profile_id)

    def test_unknown_entity_type_rejected(self, app, db, student_user):
        from app.application.file_management.file_service import (
            authorize_entity_attachment,
        )

        with app.app_context():
            with pytest.raises(FileError):
                authorize_entity_attachment(student_user, "student", 1)

    def test_missing_entity_rejected(self, app, db, student_user):
        from app.application.file_management.file_service import (
            authorize_entity_attachment,
        )

        with app.app_context():
            with pytest.raises(FileError):
                authorize_entity_attachment(student_user, "student_profile", 999999)

    def test_owner_may_attach_own_profile(self, app, db, student_user):
        from app.application.file_management.file_service import (
            authorize_entity_attachment,
        )

        with app.app_context():
            authorize_entity_attachment(
                student_user, "student_profile", student_user.student_profile.id
            )

    def test_admin_may_attach_existing_but_not_missing(
        self, app, db, admin_user, student_user
    ):
        from app.application.file_management.file_service import (
            authorize_entity_attachment,
        )

        with app.app_context():
            authorize_entity_attachment(
                admin_user, "student_profile", student_user.student_profile.id
            )
            with pytest.raises(FileError):
                authorize_entity_attachment(admin_user, "student_profile", 999999)

    def test_submission_attach_owner_teacher_admin(
        self, app, db, student_user, teacher_user, admin_user
    ):
        from app.application.file_management.file_service import (
            authorize_entity_attachment,
        )

        submission = self._submission_setup(db, student_user, teacher_user)
        outsider = self._other_student(db)
        with app.app_context():
            authorize_entity_attachment(
                student_user, "activity_submission", submission.id
            )
            authorize_entity_attachment(
                teacher_user, "activity_submission", submission.id
            )
            authorize_entity_attachment(
                admin_user, "activity_submission", submission.id
            )
            with pytest.raises(FileError):
                authorize_entity_attachment(
                    outsider, "activity_submission", submission.id
                )

    # -- download/visibility matrix ----------------------------------------

    def test_private_profile_file_visible_to_owner_not_stranger(
        self, app, db, student_user, admin_user
    ):
        from app.application.file_management.file_service import (
            can_download_file,
            upload_file,
        )

        stranger = self._other_student(db)
        with app.app_context():
            record = upload_file(
                file_storage=self._file_storage(),
                filename="doc.pdf",
                file_size=10,
                content_type="application/pdf",
                category="STUDENT_DOCUMENT",
                uploader_user_id=student_user.id,
                entity_type="student_profile",
                entity_id=student_user.student_profile.id,
                visibility="PRIVATE",
            )
            assert can_download_file(student_user, record) is True
            assert can_download_file(stranger, record) is False
            assert can_download_file(admin_user, record) is True

    def test_public_file_readable_by_any_authenticated_user(
        self, app, db, student_user
    ):
        from app.application.file_management.file_service import (
            can_download_file,
            upload_file,
        )

        stranger = self._other_student(db)
        with app.app_context():
            record = upload_file(
                file_storage=self._file_storage(),
                filename="pub.pdf",
                file_size=10,
                content_type="application/pdf",
                category="EDUCATIONAL_MATERIAL",
                uploader_user_id=student_user.id,
                entity_type="student_profile",
                entity_id=student_user.student_profile.id,
                visibility="PUBLIC",
            )
            assert can_download_file(stranger, record) is True

    def test_teacher_of_class_can_download_submission_file(
        self, app, db, student_user, teacher_user
    ):
        from app.application.file_management.file_service import (
            can_download_file,
            upload_file,
        )

        submission = self._submission_setup(db, student_user, teacher_user)
        stranger = self._other_student(db)
        with app.app_context():
            record = upload_file(
                file_storage=self._file_storage(),
                filename="hw.pdf",
                file_size=10,
                content_type="application/pdf",
                category="ACTIVITY_SUBMISSION",
                uploader_user_id=student_user.id,
                entity_type="activity_submission",
                entity_id=submission.id,
                visibility="PRIVATE",
            )
            assert can_download_file(student_user, record) is True
            assert can_download_file(teacher_user, record) is True
            assert can_download_file(stranger, record) is False

    # -- route-level enforcement --------------------------------------------

    def test_route_rejects_forged_entity(self, client, app, db, student_user):
        victim = self._other_student(db)
        self._login_session(client, student_user)
        before = StoredFileModel.query.count()
        resp = client.post(
            "/files/upload",
            data={
                "files": (io.BytesIO(b"evil"), "evil.pdf"),
                "category": "STUDENT_DOCUMENT",
                "entity_type": "student_profile",
                "entity_id": str(victim.student_profile.id),
                "visibility": "PUBLIC",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 302
        assert StoredFileModel.query.count() == before

    def test_route_accepts_own_profile_attachment(self, client, app, db, student_user):
        self._login_session(client, student_user)
        before = StoredFileModel.query.count()
        resp = client.post(
            "/files/upload",
            data={
                "files": (io.BytesIO(b"mine"), "mine.pdf"),
                "category": "STUDENT_DOCUMENT",
                "entity_type": "student_profile",
                "entity_id": str(student_user.student_profile.id),
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 302
        assert StoredFileModel.query.count() == before + 1

    def test_upload_redirect_rejects_external_referrer(
        self, client, app, db, student_user
    ):
        """An attacker-supplied Referer must not become a redirect target."""
        self._login_session(client, student_user)
        resp = client.post(
            "/files/upload",
            data={
                "files": (io.BytesIO(b"x"), "x.pdf"),
                "category": "OTHER",
            },
            content_type="multipart/form-data",
            headers={"Referer": "https://evil.example/phish"},
        )
        assert resp.status_code == 302
        location = resp.headers["Location"]
        assert "evil.example" not in location
        assert location.endswith("/auth/dashboard")

    def test_upload_redirect_allows_same_origin_referrer(
        self, client, app, db, student_user
    ):
        self._login_session(client, student_user)
        resp = client.post(
            "/files/upload",
            data={
                "files": (io.BytesIO(b"x"), "x.pdf"),
                "category": "OTHER",
            },
            content_type="multipart/form-data",
            headers={"Referer": "http://localhost/files/admin"},
        )
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/files/admin"

    def test_admin_list_clamps_per_page(self, client, app, db, admin_user):
        """Absurd per_page values must not error or reach the query raw."""
        self._login_session(client, admin_user)
        for raw in ("1000000", "-5", "0", "abc"):
            resp = client.get(f"/files/admin?per_page={raw}")
            assert resp.status_code == 200
