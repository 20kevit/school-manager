"""Audit logging application service."""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal

from app.extensions import db
from app.infrastructure.database.models import AuditLogModel

logger = logging.getLogger(__name__)


def _serialize_value(value):
    """Convert a value to a JSON-safe format."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    return str(value)


def log(
    user_id: int,
    action: str,
    entity_type: str,
    entity_id: int,
    old_values: dict | None = None,
    new_values: dict | None = None,
) -> AuditLogModel:
    """Log an audit event.

    Args:
        user_id: ID of the user who performed the action.
        action: Action performed (e.g., "CREATE", "UPDATE", "DELETE").
        entity_type: Type of entity (e.g., "ASSESSMENT_RESULT", "FINANCIAL_TRANSACTION").
        entity_id: ID of the affected entity.
        old_values: State before the change (for updates/corrections).
        new_values: State after the change.

    Returns:
        The created AuditLogModel.
    """
    serialized_old = _serialize_value(old_values) if old_values else None
    serialized_new = _serialize_value(new_values) if new_values else None

    audit_log = AuditLogModel(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=serialized_old,
        new_values=serialized_new,
    )
    db.session.add(audit_log)
    db.session.flush()

    logger.info(
        "Audit: user=%d action=%s entity=%s:%d",
        user_id,
        action,
        entity_type,
        entity_id,
    )

    return audit_log


def get_audit_logs(
    *,
    user_id: int | None = None,
    entity_type: str | None = None,
    action: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLogModel]:
    """Query audit logs with optional filters."""
    query = AuditLogModel.query

    if user_id is not None:
        query = query.filter_by(user_id=user_id)
    if entity_type is not None:
        query = query.filter_by(entity_type=entity_type)
    if action is not None:
        query = query.filter_by(action=action)
    if start_date is not None:
        query = query.filter(AuditLogModel.timestamp >= start_date)
    if end_date is not None:
        query = query.filter(AuditLogModel.timestamp <= end_date)

    return (
        query.order_by(AuditLogModel.timestamp.desc()).offset(offset).limit(limit).all()
    )


def count_audit_logs(
    *,
    user_id: int | None = None,
    entity_type: str | None = None,
    action: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> int:
    """Count audit logs with optional filters."""
    query = AuditLogModel.query

    if user_id is not None:
        query = query.filter_by(user_id=user_id)
    if entity_type is not None:
        query = query.filter_by(entity_type=entity_type)
    if action is not None:
        query = query.filter_by(action=action)
    if start_date is not None:
        query = query.filter(AuditLogModel.timestamp >= start_date)
    if end_date is not None:
        query = query.filter(AuditLogModel.timestamp <= end_date)

    return query.count()


def get_audit_log(log_id: int) -> AuditLogModel | None:
    """Get a single audit log by ID."""
    return AuditLogModel.query.get(log_id)
