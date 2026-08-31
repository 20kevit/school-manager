"""Seed script for MVP testing.

Usage::

    .venv\\Scripts\\activate
    $env:FLASK_APP="run.py"
    python seed.py

This uses db.create_all() to create tables directly from models.
Do NOT use ``flask db upgrade`` -- some migrations have SQLite compatibility issues.
"""

import os
import sys
from datetime import date

# Delete old database if it exists
db_path = os.path.join(os.path.dirname(__file__), "instance", "school_manager_dev.db")
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Deleted old database: {db_path}")

from app import create_app  # noqa: E402
from app.application.auth.services import assign_role, create_user  # noqa: E402
from app.extensions import db  # noqa: E402
from app.infrastructure.database.models import (  # noqa: E402
    ParentProfileModel,
    StudentProfileModel,
    UserModel,
)

app = create_app("development")
with app.app_context():
    # Create all tables from models (bypasses broken migrations)
    db.create_all()
    print("All tables created.")

    # Check if already seeded
    if UserModel.query.filter_by(login="admin").first() is not None:
        print("Users already exist. Skipping seed.")
        sys.exit(0)

    admin = create_user("admin", "admin123")
    assign_role(admin, "ADMIN")
    print("Created: admin / admin123")

    teacher = create_user("teacher1", "teacher123")
    assign_role(teacher, "TEACHER")
    print("Created: teacher1 / teacher123")

    student = create_user("student1", "student123")
    assign_role(student, "STUDENT")
    profile = StudentProfileModel(
        user_id=student.id,
        first_name="Ali",
        last_name="Rezaei",
        national_id="1234567890",
        mobile_phone="09121234567",
        birth_date=date(2008, 5, 15),
        gender="MALE",
    )
    db.session.add(profile)
    db.session.flush()
    print("Created: student1 / student123")

    parent = create_user("parent1", "parent123")
    assign_role(parent, "PARENT")
    parent_profile = ParentProfileModel(user_id=parent.id)
    db.session.add(parent_profile)
    db.session.flush()
    parent_profile.students.append(profile)
    print("Created: parent1 / parent123 (linked to student1)")

    db.session.commit()
    print("Seed complete.")
