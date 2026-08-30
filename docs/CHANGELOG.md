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

## P5 — Learning Activities & Homework (2026-08-30)

### Added

- Activity domain entity with enums (ActivityType, ActivityRequirement, SubmissionStatus)
- Activity database model with multi-level scope (Course, Class, Session)
- ActivitySubmission database model with versioned submission history
- ActivityFile database model for file upload tracking
- Activity application service with CRUD, submission, grading, and file management
- Course → Class activity copying (persisted, not inherited)
- Class-level activity customization independent of Course defaults
- Multiple activities per Session support
- Independent activities (no session required)
- Student submission with text content and file uploads
- Versioned submission history (each submission creates a new version)
- Late submission detection (accepts submission, marks as LATE)
- Teacher/Admin grading with score, feedback, and timestamps
- RETURNED workflow for resubmission
- File upload validation (type, size, MIME type)
- Activity deactivation (soft-disable, preserves submissions)
- Admin web UI: activity list, create/edit, detail, submissions, grading
- Teacher web UI: my classes, class activities, submissions, grading
- Student web UI: my classes, class activities, submit, history, feedback
- File download with authorization checks
- Navigation links for activity management
- Database migration for activity models
- 74 tests covering activity CRUD, types, relationships, copying, submission, grading, return/resubmission, queries, file validation, domain entities, and enrollment integration

### Design Decisions

- Activity model supports Course/Class/Session scope without complex inheritance
- Course defaults are copied to Class (persisted), not runtime-inherited
- Class customization does not modify Course defaults
- Submission versioning preserves all historical attempts
- Late submissions accepted but marked (no auto-penalty)
- RETURNED status supports teacher-student correction workflow
- File validation checks extension, size, and MIME type server-side
- Activity deactivation preserves all historical submissions

## P6 — Finance & Tuition (2026-08-30)

### Added

- FinancialTransaction domain entity with enums (TransactionType, TransactionCategory, PaymentMethod, TransactionStatus)
- FinancialTransaction database model with indexes and relationships
- Tuition field added to AcademyClass model (Numeric 12,2)
- Finance application service with charges, payments, refunds, discounts, adjustments, corrections, and reversals
- Balance derived from transactions (transaction-based ledger, not mutable balance field)
- Transaction history with signed amounts (PAYMENT/DISCOUNT positive, CHARGE/REFUND negated)
- Correction mechanism (mark original as CORRECTED, create new corrected entry)
- Reversal mechanism (keep original ACTIVE, create REVERSAL with opposite sign)
- Enrollment integration (approval → automatic tuition charge, cancellation → reversal)
- Idempotent tuition charge (duplicate prevention per enrollment)
- Tuition snapshot preserved at enrollment time
- Class financial summary (total tuition, enrolled count, collections, outstanding)
- Student balance, balance by class, student statement, transaction reports
- Debt report, credit report, revenue report, dashboard summary
- Transaction report with filters (student, category, type, date range)
- Admin web UI: finance dashboard, transactions list, create transaction, transaction detail, student statement, class financial, debt/credit/revenue reports
- Parent web UI: finance overview, child statement (limited to linked children)
- Student web UI: my-finance page (18+ age check enforced)
- Role-based access control (Admin full, Parent limited to children, Student 18+)
- ZarinPal payment gateway prepared architecturally (not implemented)
- Database migration for finance models
- 70 tests covering finance domain, services, enrollment integration, authorization, reports, and routes

### Design Decisions

- Transaction-based ledger (balance always derived, never stored)
- Sign convention: PAYMENT/DISCOUNT positive, CHARGE/REFUND negated
- Correction preserves original (CORRECTED status excluded from balance)
- Reversal keeps original ACTIVE for history, creates opposite entry
- Tuition snapshot at enrollment time preserves historical amounts
- Student finance access restricted by age (18+)
- Parent access limited to linked children via parent_student table

## P7 — Exams, Assessments & Grades (2026-08-30)

### Added

- Assessment domain entity with enums (AssessmentType, AssessmentStatus)
- AssessmentResult domain entity with enums (ResultStatus, PresenceStatus, PassFailStatus)
- GradeHistory domain entity for grade correction audit trail
- Assessment database model with class relationship, indexes, and configurable scores
- AssessmentResult database model with unique constraint (assessment_id, enrollment_id)
- GradeHistory database model with indexes for correction history
- Assessment application service with full CRUD, status lifecycle, results, bulk grading, history, reports, and CSV export
- Assessment types: FINAL_EXAM, MIDTERM, QUIZ, PROJECT, PRACTICAL, ORAL, OTHER
- Assessment statuses: DRAFT, SCHEDULED, OPEN, CLOSED, GRADED, CANCELLED
- Configurable maximum score per assessment (not hardcoded 100)
- Configurable passing score per assessment
- Automatic pass/fail calculation based on passing threshold
- Absent/Excused presence states for non-numeric results
- Grade correction history preserving previous scores and metadata
- Bulk grading interface for entire assessments
- Enrollment-based eligibility (only APPROVED enrollments eligible)
- Historical results preserved when enrollment is cancelled
- Assessment scheduling independent of class sessions
- Server-side authorization (Admin full, Teacher assigned classes, Student own results, Parent linked children)
- Admin web UI: assessment list, create, edit, detail, grading, reports, CSV export, student/class reports
- Teacher web UI: my classes, class assessments, grading, grade history
- Student web UI: my assessments, class results, result detail, CSV export
- Parent web UI: children overview, child results, result detail
- Navigation links for assessment management
- CSV export for assessment and student results with BOM for Excel compatibility
- Database migration for assessment models
- 76 tests covering assessment CRUD, types, statuses, eligibility, results, bulk grading, grade history, authorization, reports, CSV export, domain entities, and integration

### Design Decisions

- Assessment belongs to Class (not Course) for class-specific evaluations
- Grade corrections create history entries rather than overwriting
- Max score stored per assessment (not global constant)
- Passing score belongs to assessment (not global threshold)
- Results linked via Enrollment (consistent with Attendance pattern)
- Historical data preserved through enrollment cancellation
- Assessment scheduling independent of session schedule
- Extensible type system supports future assessment categories

## P8 — Portals (2026-08-30)

### Added

- Portal module with role-specific dashboards
- Student dashboard: enrolled classes, academic summary (average, pass/fail), attendance summary (present/absent/late), financial balance (18+ only), recent results
- Parent dashboard: children overview, per-child academic/attendance/finance summaries
- Teacher dashboard: assigned classes, class summaries (enrolled students, assessments, averages, pass rates), pending grading counts
- Admin dashboard: quick stats (students, teachers, classes, enrollments, assessments), pending enrollment requests, financial summary (payments, debtors), recent classes
- Portal service aggregating data from enrollment, assessment, attendance, finance, and academy modules
- Portal blueprint registered and integrated
- Main dashboard redirect to role-specific portal (auth.dashboard → portal.*_dashboard)
- 4 role-specific templates with Persian RTL UI

### Design Decisions

- Portal is a pure aggregation layer — no new domain entities or database tables
- All dashboard data comes from existing services (no duplicate data access)
- Main auth.dashboard redirects to role-specific portal routes
- Finance visibility follows existing age-18+ restriction for students
- Student financial balance only shown for adults (18+)
- Portal service reuses existing service functions for data access

## P9 — Notifications
