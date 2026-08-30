# Project Status

**Current Phase:** P4 — Attendance — Completed
**Current Objective:** Complete P4 — Attendance.

**Previous Phase:** P3 — Enrollment

## Status

P3 — Enrollment is in progress.

## Completed

### P0 — Foundation
- [x] Git repository initialized
- [x] Project structure created
- [x] Flask application factory
- [x] Configuration system (dev/test/prod)
- [x] Environment configuration (.env)
- [x] SQLAlchemy + Flask-Migrate setup
- [x] Health check endpoint
- [x] Testing infrastructure (pytest)
- [x] Basic tests (app creation, health endpoint)
- [x] Code quality tooling (Ruff)
- [x] Documentation (README, ARCHITECTURE, DEVELOPMENT, PROJECT_STATUS, TODO, CHANGELOG)
- [x] Architecture Decision Records
- [x] Project roadmap established

### P1 — Identity & Access
- [x] User model with password hashing (Werkzeug)
- [x] Role-based access control (ADMIN, TEACHER, STUDENT, PARENT)
- [x] StudentProfile with national_id, birth_date, gender
- [x] TeacherProfile
- [x] ParentProfile with parent-student many-to-many
- [x] Flask-Login session management
- [x] Authentication (login, logout, session)
- [x] Authorization (role_required decorator)
- [x] Password change
- [x] Student initial login (national_id as login/password)
- [x] Persian RTL UI templates
- [x] Database migration (initial schema)
- [x] 44 tests passing

### P2 — Academy Structure
- [x] Course model (title, description, num_sessions, age range, prerequisites)
- [x] Syllabus items (ordered, per-course content)
- [x] Academy Class model (course, title, dates, capacity, status)
- [x] Teacher assignment (single teacher per class, extendable)
- [x] Weekly class schedule (multiple weekdays, different times)
- [x] Session generation from schedule (persisted records)
- [x] Session rescheduling (individual session date/time change)
- [x] Session cancellation (preserves record, changes status)
- [x] Session shifting (regenerate remaining sessions after cancellation)
- [x] Session content overrides (class-level customization)
- [x] Admin authorization for all academy routes
- [x] Web UI: Course list, create, edit, detail
- [x] Web UI: Syllabus management (add, update, delete)
- [x] Web UI: Class list, create, edit, detail
- [x] Web UI: Weekly schedule display
- [x] Web UI: Session list, detail, reschedule, cancel, complete
- [x] Database migration for academy structure
- [x] 114 tests passing

### P3 — Enrollment
- [x] Enrollment domain entity with status lifecycle
- [x] Student enrollment requests
- [x] Admin direct enrollment with auto-approval
- [x] Enrollment approval with capacity checks
- [x] Enrollment rejection and cancellation
- [x] Duplicate active enrollment prevention
- [x] Admin web UI for enrollment management
- [x] Student web UI for enrollment requests
- [x] Database migration for enrollment model
- [x] 140 tests passing

### P4 — Attendance
- [x] Attendance domain entity with status enum (PRESENT, ABSENT, LATE, EXCUSED)
- [x] Attendance database model with unique constraint (enrollment_id, session_id)
- [x] Attendance application service (record, bulk record, query, summary)
- [x] Enrollment/Session same-class validation
- [x] Approved enrollment requirement
- [x] One attendance per student per session enforcement
- [x] Bulk attendance recording for entire sessions
- [x] Teacher authorization (own classes only)
- [x] Admin full access
- [x] Student attendance history view
- [x] Admin web UI: session list with attendance summary
- [x] Teacher web UI: my classes, sessions, take attendance
- [x] Student web UI: my attendance history
- [x] Attendance summary computation
- [x] Historical attendance preservation (cancelled enrollment)
- [x] Database migration for attendance model
- [x] 174 tests passing
