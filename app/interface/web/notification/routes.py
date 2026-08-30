"""Notification routes — admin management and user views."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.application.notification.notification_service import (
    NotificationError,
    cancel_notification,
    count_notifications,
    count_unread_in_app,
    get_failed_notifications,
    get_notification,
    get_notification_deliveries,
    get_user_in_app_notifications,
    list_notifications,
    mark_all_in_app_read,
    mark_in_app_read,
    retry_notification,
    send_announcement,
    send_manual_notification,
)
from app.application.notification.preference_service import (
    get_preference_matrix,
    update_preferences_bulk,
)
from app.application.notification.template_service import (
    TemplateError,
    create_template,
    delete_template,
    get_template,
    list_templates,
    update_template,
)
from app.domain.notification import (
    NotificationChannel,
    NotificationType,
)
from app.infrastructure.database.models import UserModel
from app.infrastructure.notification.registry import get_provider_health
from app.interface.web.decorators import role_required

notification_bp = Blueprint("notification", __name__, url_prefix="/notification")


# ---------------------------------------------------------------------------
# Admin — Dashboard & History
# ---------------------------------------------------------------------------


@notification_bp.route("/admin")
@login_required
@role_required("ADMIN")
def admin_dashboard():
    """Admin notification dashboard with overview."""
    status_filter = request.args.get("status", "")
    type_filter = request.args.get("type", "")
    page = request.args.get("page", 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    notifications = list_notifications(
        status=status_filter or None,
        notification_type=type_filter or None,
        limit=per_page,
        offset=offset,
    )
    total = count_notifications(status=status_filter or None)
    total_pages = max(1, (total + per_page - 1) // per_page)
    failed = get_failed_notifications(limit=10)
    provider_health = get_provider_health()

    return render_template(
        "notification/admin_dashboard.html",
        notifications=notifications,
        failed=failed,
        provider_health=provider_health,
        selected_status=status_filter,
        selected_type=type_filter,
        page=page,
        total_pages=total_pages,
        total=total,
    )


@notification_bp.route("/admin/<int:notification_id>")
@login_required
@role_required("ADMIN")
def admin_detail(notification_id):
    """View notification detail with delivery records."""
    notification = get_notification(notification_id)
    if notification is None:
        flash("Notification not found.", "error")
        return redirect(url_for("notification.admin_dashboard"))

    deliveries = get_notification_deliveries(notification_id)
    recipient = UserModel.query.get(notification.recipient_user_id)

    return render_template(
        "notification/admin_detail.html",
        notification=notification,
        deliveries=deliveries,
        recipient=recipient,
    )


@notification_bp.route("/admin/<int:notification_id>/retry", methods=["POST"])
@login_required
@role_required("ADMIN")
def admin_retry(notification_id):
    """Retry a failed notification."""
    try:
        retry_notification(notification_id)
        flash("Notification retried.", "success")
    except NotificationError as e:
        flash(str(e), "error")

    return redirect(
        url_for("notification.admin_detail", notification_id=notification_id)
    )


@notification_bp.route("/admin/<int:notification_id>/cancel", methods=["POST"])
@login_required
@role_required("ADMIN")
def admin_cancel(notification_id):
    """Cancel a pending notification."""
    try:
        cancel_notification(notification_id)
        flash("Notification cancelled.", "success")
    except NotificationError as e:
        flash(str(e), "error")

    return redirect(
        url_for("notification.admin_detail", notification_id=notification_id)
    )


# ---------------------------------------------------------------------------
# Admin — Manual Notification
# ---------------------------------------------------------------------------


@notification_bp.route("/admin/manual", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def admin_manual():
    """Send a manual notification."""
    if request.method == "POST":
        try:
            recipient_ids = request.form.getlist("recipients", type=int)
            channel = request.form["channel"]
            title = request.form["title"]
            message = request.form["message"]

            if not recipient_ids:
                flash("Please select at least one recipient.", "error")
            elif not title or not message:
                flash("Title and message are required.", "error")
            else:
                send_manual_notification(
                    recipient_user_ids=recipient_ids,
                    channel=NotificationChannel(channel),
                    title=title,
                    message=message,
                )
                flash("Notification sent.", "success")
                return redirect(url_for("notification.admin_dashboard"))
        except Exception as e:
            flash(f"Error: {e}", "error")

    users = UserModel.query.filter_by(is_active_user=True).all()
    return render_template("notification/admin_manual.html", users=users)


# ---------------------------------------------------------------------------
# Admin — Announcements
# ---------------------------------------------------------------------------


@notification_bp.route("/admin/announcement", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def admin_announcement():
    """Send an announcement."""
    if request.method == "POST":
        try:
            recipient_ids = request.form.getlist("recipients", type=int)
            channels = request.form.getlist("channels")
            title = request.form["title"]
            message = request.form["message"]

            if not recipient_ids:
                flash("Please select at least one recipient.", "error")
            elif not channels:
                flash("Please select at least one channel.", "error")
            elif not title or not message:
                flash("Title and message are required.", "error")
            else:
                channel_enums = [NotificationChannel(c) for c in channels]
                send_announcement(
                    title=title,
                    message=message,
                    channels=channel_enums,
                    recipient_user_ids=recipient_ids,
                )
                flash("Announcement sent.", "success")
                return redirect(url_for("notification.admin_dashboard"))
        except Exception as e:
            flash(f"Error: {e}", "error")

    users = UserModel.query.filter_by(is_active_user=True).all()
    return render_template("notification/admin_announcement.html", users=users)


# ---------------------------------------------------------------------------
# Admin — Templates
# ---------------------------------------------------------------------------


@notification_bp.route("/admin/templates")
@login_required
@role_required("ADMIN")
def admin_templates():
    """List notification templates."""
    templates = list_templates()
    return render_template("notification/admin_templates.html", templates=templates)


@notification_bp.route("/admin/templates/create", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def admin_template_create():
    """Create a notification template."""
    if request.method == "POST":
        try:
            create_template(
                name=request.form["name"],
                notification_type=NotificationType(request.form["notification_type"]),
                channel=NotificationChannel(request.form["channel"]),
                body=request.form["body"],
                subject=request.form.get("subject", ""),
            )
            flash("Template created.", "success")
            return redirect(url_for("notification.admin_templates"))
        except TemplateError as e:
            flash(str(e), "error")

    return render_template("notification/admin_template_form.html")


@notification_bp.route(
    "/admin/templates/<int:template_id>/edit", methods=["GET", "POST"]
)
@login_required
@role_required("ADMIN")
def admin_template_edit(template_id):
    """Edit a notification template."""
    template = get_template(template_id)
    if template is None:
        flash("Template not found.", "error")
        return redirect(url_for("notification.admin_templates"))

    if request.method == "POST":
        try:
            update_template(
                template_id=template_id,
                name=request.form["name"],
                subject=request.form.get("subject", ""),
                body=request.form["body"],
            )
            flash("Template updated.", "success")
            return redirect(url_for("notification.admin_templates"))
        except TemplateError as e:
            flash(str(e), "error")

    return render_template("notification/admin_template_form.html", template=template)


@notification_bp.route("/admin/templates/<int:template_id>/delete", methods=["POST"])
@login_required
@role_required("ADMIN")
def admin_template_delete(template_id):
    """Delete a notification template."""
    try:
        delete_template(template_id)
        flash("Template deleted.", "success")
    except TemplateError as e:
        flash(str(e), "error")

    return redirect(url_for("notification.admin_templates"))


# ---------------------------------------------------------------------------
# User — Notifications
# ---------------------------------------------------------------------------


@notification_bp.route("/my")
@login_required
def my_notifications():
    """List current user's in-app notifications."""
    notifications = get_user_in_app_notifications(current_user.id)
    unread_count = count_unread_in_app(current_user.id)
    return render_template(
        "notification/my_notifications.html",
        notifications=notifications,
        unread_count=unread_count,
    )


@notification_bp.route("/my/<int:in_app_id>/read", methods=["POST"])
@login_required
def my_mark_read(in_app_id):
    """Mark a single notification as read."""
    try:
        mark_in_app_read(in_app_id, current_user.id)
    except NotificationError:
        pass
    return redirect(url_for("notification.my_notifications"))


@notification_bp.route("/my/read-all", methods=["POST"])
@login_required
def my_mark_all_read():
    """Mark all notifications as read."""
    mark_all_in_app_read(current_user.id)
    flash("All notifications marked as read.", "success")
    return redirect(url_for("notification.my_notifications"))


# ---------------------------------------------------------------------------
# User — Preferences
# ---------------------------------------------------------------------------


@notification_bp.route("/preferences", methods=["GET", "POST"])
@login_required
def my_preferences():
    """View and update notification preferences."""
    if request.method == "POST":
        preferences = []
        for notif_type in NotificationType:
            for channel in NotificationChannel:
                if channel == NotificationChannel.IN_APP:
                    continue
                key = f"{notif_type}_{channel}"
                enabled = request.form.get(key) == "on"
                preferences.append(
                    {
                        "notification_type": notif_type,
                        "channel": channel,
                        "enabled": enabled,
                    }
                )
        update_preferences_bulk(current_user.id, preferences)
        flash("Preferences updated.", "success")
        return redirect(url_for("notification.my_preferences"))

    matrix = get_preference_matrix(current_user.id)
    return render_template("notification/my_preferences.html", matrix=matrix)
