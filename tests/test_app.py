"""Tests for application factory and basic endpoints."""


def test_app_creation(app):
    """Test that the application can be created."""
    assert app is not None


def test_app_is_testing(app):
    """Test that the application is in testing mode."""
    assert app.config["TESTING"] is True


def test_health_endpoint(client):
    """Test that the health endpoint returns ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    assert response.get_json()["database"] == "ok"


def test_health_endpoint_reports_database_outage(client):
    """Health must return 503 (not 200/500) when the database is down."""
    from unittest.mock import MagicMock, patch

    from sqlalchemy.exc import OperationalError

    from app.extensions import db

    broken = MagicMock()
    broken.execute.side_effect = OperationalError(
        "SELECT 1", {}, Exception("connection refused")
    )
    with patch.object(db, "session", broken):
        response = client.get("/health")
    assert response.status_code == 503
    payload = response.get_json()
    assert payload["status"] == "degraded"
    assert payload["database"] == "error"


def test_index(client):
    """Test that the index page loads."""
    response = client.get("/")
    assert response.status_code == 200
