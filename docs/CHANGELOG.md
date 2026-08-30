# Changelog

All notable project-level changes are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Added

- Project structure with modular monolith architecture
- Flask application factory pattern
- Configuration system (development, testing, production)
- Environment variable support via `.env`
- SQLAlchemy + Flask-Migrate for database
- Health check endpoint (`/health`)
- Testing infrastructure with pytest
- Code quality tooling with Ruff
- Base HTML template and static assets
- Documentation: README, ARCHITECTURE, DEVELOPMENT, PROJECT_STATUS, TODO, CHANGELOG
- Architecture Decision Records (ADR-001 through ADR-003)

### Changed

- Established project roadmap (P0 through P11) and updated project status to P1 — Identity & Access

## P1 — Identity & Access (2026-08-30)

### Added

- User model with password hashing (Werkzeug)
- Role-based access control (ADMIN, TEACHER, STUDENT, PARENT)
- StudentProfile with national_id, birth_date, gender
- TeacherProfile
- ParentProfile with parent-student many-to-many relationship
- Flask-Login session management
- Authentication blueprint (login, logout, dashboard, change-password)
- Authorization decorator (`role_required`)
- Persian RTL UI templates (login, dashboard, change-password)
- Student initial login (national_id as login and initial password)
- Database migration for identity and access models
- 44 tests covering User, Roles, Profiles, Authentication, Authorization
