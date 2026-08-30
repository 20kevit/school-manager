"""Storage abstraction — interface and local implementation."""

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from flask import current_app


class StorageBackend(ABC):
    """Abstract storage backend interface.

    Application/domain code depends on this abstraction,
    never on concrete filesystem operations.
    """

    @abstractmethod
    def save(self, key: str, file_data: bytes) -> None:
        """Save file data to storage."""

    @abstractmethod
    def save_stream(self, key: str, file_stream) -> int:
        """Save a file stream to storage. Returns bytes written."""

    @abstractmethod
    def open(self, key: str):
        """Open a file for reading. Returns a file-like object."""

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a file from storage. Returns True if deleted."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a file exists in storage."""

    @abstractmethod
    def replace(self, key: str, file_data: bytes) -> None:
        """Replace an existing file's contents."""

    @abstractmethod
    def get_size(self, key: str) -> int:
        """Get the size of a stored file."""


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, base_path: str):
        if not base_path:
            import tempfile

            base_path = os.path.join(tempfile.gettempdir(), "school_manager_storage")
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def _resolve_path(self, key: str) -> str:
        """Resolve a storage key to an absolute filesystem path."""
        safe_key = key.replace("\\", "/").lstrip("/")
        # Prevent path traversal
        resolved = os.path.normpath(os.path.join(self.base_path, safe_key))
        if not resolved.startswith(os.path.normpath(self.base_path)):
            raise ValueError(f"Path traversal detected: {key}")
        return resolved

    def save(self, key: str, file_data: bytes) -> None:
        path = self._resolve_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(file_data)

    def save_stream(self, key: str, file_stream) -> int:
        path = self._resolve_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        total = 0
        with open(path, "wb") as f:
            while True:
                chunk = file_stream.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                total += len(chunk)
        return total

    def open(self, key: str):
        path = self._resolve_path(key)
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {key}")
        return open(path, "rb")

    def delete(self, key: str) -> bool:
        path = self._resolve_path(key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def exists(self, key: str) -> bool:
        path = self._resolve_path(key)
        return os.path.exists(path)

    def replace(self, key: str, file_data: bytes) -> None:
        path = self._resolve_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(file_data)

    def get_size(self, key: str) -> int:
        path = self._resolve_path(key)
        return os.path.getsize(path)


def generate_storage_key(category: str, extension: str) -> str:
    """Generate a safe, unique storage key.

    Format: files/YYYY/MM/uuid.ext
    """
    now = datetime.now()
    unique = uuid.uuid4().hex
    safe_ext = extension.lstrip(".").lower()
    return f"files/{now.year}/{now.month:02d}/{unique}.{safe_ext}"


def get_storage_backend() -> LocalStorageBackend:
    """Get the configured storage backend."""
    storage_path = current_app.config.get("FILE_STORAGE_PATH", "")
    if not storage_path:
        storage_path = os.path.join(current_app.instance_path, "storage")
    return LocalStorageBackend(storage_path)
