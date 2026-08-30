import pytest

from app import create_app


@pytest.fixture(scope="session")
def app():
    """Create application for testing."""
    app = create_app("testing")
    return app


@pytest.fixture(scope="session")
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture(scope="session")
def runner(app):
    """Create a test runner."""
    return app.test_cli_runner()
