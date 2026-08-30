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

## P3 — Enrollment (2026-08-30)

### Added

- Enrollment domain entity with status enum (PENDING, APPROVED, REJECTED, CANCELLED)
- Enrollment database model with timestamps and relationships
- Enrollment application service with lifecycle management
- Student enrollment request functionality
- Admin direct enrollment with optional auto-approval
- Enrollment approval with capacity and duplicate checks
- Enrollment rejection with timestamp preservation
- Enrollment cancellation for pending and approved enrollments
- Duplicate active enrollment prevention (application and database level)
- Class capacity enforcement at approval time
- Admin web UI: enrollment list, pending requests, enrollment details, direct enrollment form
- Student web UI: available classes, class details, enrollment request, my enrollments
- Navigation links for enrollment management
- Database migration for enrollment model
- Enrollment repository interface
- 20+ tests covering enrollment lifecycle, capacity, and authorization

### Design Decisions

- Student vs Admin enrollment: Students request (PENDING), Admins may auto-approve
- Duplicate prevention: Only one active enrollment per student per class
- Capacity enforcement: Checked at approval time, not at request time
- Historical records: Rejected and cancelled enrollments preserved for tracking
- Basic eligibility: Only essential checks at this phase (extensible for future)

## P4 — Attendance (2026-08-30)

### Added

- Attendance domain entity with status enum (PRESENT, ABSENT, LATE, EXCUSED)
- Attendance database model with unique constraint (enrollment_id, session_id)
- Attendance application service with record, bulk record, query, and summary functions
- Enrollment/Session same-class validation
- Approved enrollment requirement for attendance
- One attendance per student per session enforcement (application + database level)
- Bulk attendance recording for entire sessions in a single operation
- Teacher authorization (attendance only for assigned classes)
- Admin full access to all attendance
- Student attendance history view
- Admin web UI: session list with attendance summary, take attendance
- Teacher web UI: my classes, class sessions, take attendance
- Student web UI: my attendance history with summary
- Attendance summary computation (present/absent/late/excused counts)
- Historical attendance preservation (cancelled enrollment does not delete records)
- Database migration for attendance model
- 34 new tests covering attendance creation, integrity, duplicates, bulk recording, authorization, and UI routes

### Design Decisions

- Attendance linked via Enrollment (not directly to Student) to enforce class membership
- Unique constraint on (enrollment_id, session_id) prevents duplicate attendance
- Updating existing attendance modifies in-place rather than creating new records
- Cancelled enrollments preserve historical attendance records
- Teachers authorized server-side via class assignment, not just UI hiding
