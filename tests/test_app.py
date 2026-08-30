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


def test_index(client):
    """Test that the index page loads."""
    response = client.get("/")
    assert response.status_code == 200
