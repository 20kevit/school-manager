import pytest

from app import create_app
from app.extensions import db as _db
from app.infrastructure.database.models import (
    RoleModel,
    StudentProfileModel,
    UserModel,
)
from app.interface.web.decorators import role_required


@pytest.fixture(scope="session")
def app():
    """Create application for testing."""
    app = create_app("testing")

    @app.route("/admin-only")
    @role_required("ADMIN")
    def admin_only():
        return "admin content"

    @app.route("/admin-only-2")
    @role_required("ADMIN")
    def admin_only_2():
        return "admin content"

    @app.route("/admin-only-3")
    @role_required("ADMIN")
    def admin_only_3():
        return "admin content"

    return app


@pytest.fixture(scope="function")
def db(app):
    """Create a fresh database for each test."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app, db):
    """Create a test client with a fresh database."""
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app, db):
    """Create a test runner with a fresh database."""
    return app.test_cli_runner()


@pytest.fixture
def sample_user(db):
    """Create a sample user for testing."""
    user = UserModel(login="testuser")
    user.set_password("testpass123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin user for testing."""
    user = UserModel(login="admin")
    user.set_password("adminpass123")
    role = RoleModel(name="ADMIN")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def teacher_user(db):
    """Create a teacher user for testing."""
    user = UserModel(login="teacher")
    user.set_password("teacherpass123")
    role = RoleModel(name="TEACHER")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def student_user(db):
    """Create a student user for testing."""
    from datetime import date

    user = UserModel(login="student")
    user.set_password("studentpass123")
    role = RoleModel(name="STUDENT")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.flush()

    profile = StudentProfileModel(
        user_id=user.id,
        first_name="Ali",
        last_name="Rezaei",
        national_id="1234567890",
        mobile_phone="09121234567",
        birth_date=date(2000, 1, 15),
        gender="MALE",
    )
    db.session.add(profile)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def parent_user(db):
    """Create a parent user for testing."""
    user = UserModel(login="parent")
    user.set_password("parentpass123")
    role = RoleModel(name="PARENT")
    db.session.add(role)
    db.session.flush()
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user
