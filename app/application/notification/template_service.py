"""Notification template application service."""

from __future__ import annotations

from app.domain.notification import NotificationChannel, NotificationType
from app.extensions import db
from app.infrastructure.database.models import NotificationTemplateModel


class TemplateError(Exception):
    """Raised when a template operation fails."""


def create_template(
    name: str,
    notification_type: NotificationType,
    channel: NotificationChannel,
    body: str,
    subject: str = "",
    is_active: bool = True,
) -> NotificationTemplateModel:
    """Create a notification template."""
    existing = NotificationTemplateModel.query.filter_by(name=name).first()
    if existing:
        raise TemplateError(f"Template with name '{name}' already exists.")

    template = NotificationTemplateModel(
        name=name,
        notification_type=notification_type,
        channel=channel,
        subject=subject,
        body=body,
        is_active=is_active,
    )
    db.session.add(template)
    db.session.commit()
    return template


def update_template(
    template_id: int,
    name: str | None = None,
    subject: str | None = None,
    body: str | None = None,
    is_active: bool | None = None,
) -> NotificationTemplateModel:
    """Update a notification template."""
    template = NotificationTemplateModel.query.get(template_id)
    if template is None:
        raise TemplateError("Template not found.")

    if name is not None:
        existing = NotificationTemplateModel.query.filter_by(name=name).first()
        if existing and existing.id != template_id:
            raise TemplateError(f"Template with name '{name}' already exists.")
        template.name = name

    if subject is not None:
        template.subject = subject
    if body is not None:
        template.body = body
    if is_active is not None:
        template.is_active = is_active

    db.session.commit()
    return template


def get_template(template_id: int) -> NotificationTemplateModel | None:
    """Get a template by ID."""
    return NotificationTemplateModel.query.get(template_id)


def get_template_by_name(name: str) -> NotificationTemplateModel | None:
    """Get a template by name."""
    return NotificationTemplateModel.query.filter_by(name=name).first()


def list_templates(
    notification_type: str | None = None,
    channel: str | None = None,
    active_only: bool = False,
) -> list[NotificationTemplateModel]:
    """List templates with optional filters."""
    query = NotificationTemplateModel.query
    if notification_type:
        query = query.filter_by(notification_type=notification_type)
    if channel:
        query = query.filter_by(channel=channel)
    if active_only:
        query = query.filter_by(is_active=True)
    return query.order_by(NotificationTemplateModel.name).all()


def render_template(
    template_id: int,
    context: dict[str, str],
) -> tuple[str, str]:
    """Render a template with context variables.

    Returns (subject, body).
    """
    template = NotificationTemplateModel.query.get(template_id)
    if template is None:
        raise TemplateError("Template not found.")

    if not template.is_active:
        raise TemplateError("Template is inactive.")

    subject = template.subject
    body = template.body
    for key, value in context.items():
        placeholder = "{{ " + key + " }}"
        subject = subject.replace(placeholder, str(value))
        body = body.replace(placeholder, str(value))

    return subject, body


def delete_template(template_id: int) -> None:
    """Delete a notification template."""
    template = NotificationTemplateModel.query.get(template_id)
    if template is None:
        raise TemplateError("Template not found.")
    db.session.delete(template)
    db.session.commit()
