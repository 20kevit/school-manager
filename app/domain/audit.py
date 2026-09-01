"""Audit logging domain entity."""

from __future__ import annotations

from datetime import datetime


class AuditLog:
    """Audit log domain entity — tracks changes to sensitive data."""

    def __init__(
        self,
        id: int | None,
        user_id: int,
        action: str,
        entity_type: str,
        entity_id: int,
        old_values: dict | None = None,
        new_values: dict | None = None,
        timestamp: datetime | None = None,
    ):
        self.id = id
        self.user_id = user_id
        self.action = action
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.old_values = old_values or {}
        self.new_values = new_values or {}
        self.timestamp = timestamp or datetime.now()

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action!r} "
            f"entity={self.entity_type}:{self.entity_id} "
            f"user={self.user_id}>"
        )
