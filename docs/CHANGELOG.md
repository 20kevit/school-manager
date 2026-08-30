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

## P2 — Academy Structure (2026-08-30)

### Added

- Course model with title, description, num_sessions, age range, prerequisites
- Syllabus items for ordered course content planning
- Academy Class model with capacity at class level (not course)
- Teacher assignment structure (single teacher, extendable to multiple)
- Weekly class schedule supporting multiple weekdays with different times
- Session generation from class schedule (persisted records, not dynamic)
- Individual session rescheduling without changing recurring schedule
- Session cancellation preserving session records with CANCELLED status
- Session shifting after cancellation (regenerate remaining sessions)
- Class-specific session content overrides (3-level hierarchy: Course → Class → Session)
- Admin authorization for all academy management routes
- Persian RTL web UI for course management
- Persian RTL web UI for class management with schedule builder
- Persian RTL web UI for session management (list, detail, reschedule, cancel, complete)
- Database migration for academy structure models
- 70 new tests covering Course, Syllabus, Class, Schedule, Session operations

### Design Decisions

- Course vs Class: Course is a reusable template; Class is a running instance
- Session persistence: Sessions are real database records, not dynamically calculated
- Schedule exceptions: Individual sessions can have custom dates without modifying the recurring schedule
- Session shifting: Cancelling and shifting preserves session numbering and total count
- Content overrides: 3-level hierarchy allows Course → Class → Session customization
