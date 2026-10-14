# Changelog

All notable project-level changes are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Added
- Isolated demo environment (`demofca.20kevit.ir`): separate checkout,
  venv, systemd service (`school-manager-demo`, port 8101), PostgreSQL
  database/role (`school_manager_demo`), env file, uploads, Nginx vhost
  with Let's Encrypt TLS; see `docs/DEMO.md`
- Deterministic, idempotent, guarded synthetic-academy generator
  (`app/demo_seed_full.py`, `flask demo-seed` / `flask demo-reset --yes`):
  125 users, 10 courses, 40 classes, 229 enrollments, 624 sessions, 1320
  attendances, 40 assessments, ~252 finance transactions via real
  services, payroll, activities, calendar, notifications; shared demo
  password `12345678` (hashed, demo-only)
- 12 demo tests (`tests/test_demo_seed.py`): guard refusals, determinism,
  idempotency, relationship integrity, finance reconciliation, hashing

### Added
- Administrator dashboard redesign (production-quality): role-specific
  student/teacher counts, operational class statuses, distinct course counts,
  enrollment request vs approved vs unique-student metrics, OPEN/CLOSED
  assessment follow-ups, prioritized attention list, today's sessions with
  attendance-recording status, financial pulse on canonical finance
  definitions (gross/net month collections, billed vs collected, top
  debtors), two CSS-only trend charts with data-table alternatives, empty and
  error states, responsive RTL layout; `docs/ADMIN_DASHBOARD.md` documents
  every metric; 22 new tests in `tests/test_admin_dashboard.py`
- Fixed mobile horizontal overflow globally via flex-item `min-width: 0` on
  `.main-content` (also fixed the class list page) and wrapped bar-chart
  labels/values
- Verification fixes: today sessions without approved enrollments are
  neutral (never flagged, excluded from completion rate); enrollment admin
  list accepts all valid status filters so KPI cards link to exact
  populations; students KPI links to the role-filtered user list
- Dashboard redesign iteration 2: whole-card clickable KPI anchors;
  server-rendered SVG charts (12-month net/gross collections, monthly
  requests vs approvals, 7-day attendance completion) with tabular
  alternatives; canonical `finance_service.get_monthly_revenue()` grouped
  query; grouped enrollment/attendance/capacity aggregates (~40% fewer
  dashboard queries); class-list status filter; capacity attention items;
  `compact_number` template filter; `beautifulsoup4` test dependency

### Security
- Payment failure callbacks isolated behind provider verification (unsigned
  `Status=NOK` can no longer fail pending payments); transport errors leave
  payments PENDING for retry; whole-Toman initiation guard
- Logout is POST-only (CSRF-safe); app-level X-Frame-Options/nosniff/
  Referrer-Policy headers
- 78 exception-leaking flashes converted to server-side logging + generic
  user message; upload redirects restricted to same-origin; per_page clamped
- Upload byte path validates size/MIME; profile photos sanitized; activity
  downloads force attachment
- Transcript route scoped to the teacher's own classes (IDOR fix)
- Bootstrap national-ID passwords force rotation at first login; predictable
  new passwords rejected; admin resets force rotation
- DB-backed login throttling (per-account + per-IP sliding window, no lockout)
- Production refuses to boot on missing/default `SECRET_KEY`
- File uploads: category/visibility allow-lists, entity authorization,
  entity-scoped reads, sanitized filenames
- SMS provider reports unimplemented delivery as failure (no fake success)

### Financial integrity
- Refund cap accounts linked reversals; corrections reject rewritten money
  rows and re-point live children at the corrected copy; cancellation
  reversals use the audited single-use path; audit amounts serialize exactly
- One canonical net-collected definition shared by finance and reporting
  surfaces; dashboard billed-vs-collected and overview gross figures renamed
  honestly; class summary adds gross debtor exposure; operational debtor
  count uses signed CASE (was raw SUM, missed debtors)
- Admin amounts parsed as Decimal (was binary float); seeds store exact
  Decimals; currency filter uses Decimal formatting
- Adjustments stored signed; reversal math negates signed entries
- Linked refunds validated against the original payment and capped at the
  remaining refundable amount; transactions reversible only once
- Online callbacks idempotent with immutable authority (`gateway_ref_id`)
- Percentage payroll counts all class payment channels (was TUITION-only)
- One payroll payment per teacher-period (unique constraint); deductions bounded

### Reliability
- Notification handler contract fixed; event-key deduplication + unique index
- Reminder jobs idempotent with owned cadence; systemd timer templates in `deploy/`
- Fresh PostgreSQL upgrades verified to head (boolean defaults fixed, missing
  audit/file tables added); PG migration check added to CI

### Tests
- Full suite green: 993 passed, 5 PG-gated skipped, 0 failed; ruff clean
- Session-regeneration tests made date-relative (were wall-clock fragile)
- Python policy pinned to 3.12 across docs and CI; demo credentials marked local-only

## P27 — Deployment Readiness (Docker & Production Config) (2026-09-01)

### Added
- Multi-stage `Dockerfile` based on Python 3.12-slim with non-root `appuser`
- `docker-compose.yml` orchestrating PostgreSQL 15, Flask (Gunicorn), and Nginx
- `.dockerignore` to exclude dev artifacts from Docker image
- `wsgi.py` as dedicated Gunicorn entry point
- `gunicorn_config.py` with configurable workers, timeout (120s), and logging
- `entrypoint.sh` script: waits for PostgreSQL, runs migrations, conditionally seeds based on `SEED_MODE` env var (`demo`, `basic`, or empty to skip)
- `nginx/nginx.conf` with reverse proxy, static file serving, gzip compression, and upload size limit
- `docs/DEPLOYMENT.md` with step-by-step deployment instructions
- `.env` with Docker-appropriate default configuration

### Changed
- `config/__init__.py`: Added `SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}` to `ProductionConfig` for PostgreSQL connection reliability
- `README.md`: Added Production Deployment section and Deployment Guide link

### Design Decisions
- Entrypoint seeding is conditional via `SEED_MODE` env var: `demo` (rich data), `basic` (roles/admin only), or empty (skip) — safe for real production
- Gunicorn uses `wsgi:app` to align with dedicated `wsgi.py` entry point
- Multi-stage Docker build separates build dependencies (gcc, libpq-dev) from runtime image
- Nginx serves static files directly for performance; uploads shared via Docker volume
- Scheduler remains in-process (idempotent, safe with multiple workers); documented for future consideration

### Metrics
- 905 tests passing (unchanged)
- Ruff check and format clean
- Docker image built and verified

## P26 — Automated Tasks & Audit Logging (2026-09-01)

### Added
- Lightweight background scheduler (`app/scheduler.py`) using daemon threads
- Daily automated class reminder: sends in-app notifications to enrolled students for tomorrow's sessions
- Weekly automated payment reminder: sends in-app notifications to students with outstanding debt
- CLI commands: `flask run-scheduler` (continuous loop), `flask run-jobs` (one-shot execution)
- Scheduler auto-starts on app creation (except in testing mode)
- `AuditLog` domain entity (`app/domain/audit.py`) for tracking sensitive data changes
- `AuditLogModel` database table with indexes on user, action, entity, and timestamp
- `AuditService` application service: `log()`, `get_audit_logs()`, `count_audit_logs()`
- Audit logging integrated into `assessment_service.record_result()` — captures old/new state on grade corrections
- Audit logging integrated into `assessment_service.update_result()` — captures old/new state on grade corrections
- Audit logging integrated into `finance_service.correct_transaction()` — captures old/new state on corrections
- Audit logging integrated into `finance_service.reverse_transaction()` — captures old/new state on reversals
- Admin route `/admin/audit-logs` with filterable table (user, entity type, action, date range)
- Admin sidebar link "گزارش تغییرات" for audit log access
- Audit log template with expandable JSON diff view for old/new values
- 19 new tests covering audit service, assessment audit integration, finance audit integration, scheduler jobs, and admin routes

### Design Decisions
- Scheduler uses `threading.Thread` with `daemon=True` — no external dependencies (no Celery, no Redis)
- Scheduler runs hourly interval, checks for daily/weekly jobs based on date
- Audit logs use JSON columns for old/new values with automatic datetime/Decimal serialization
- Audit logging is additive — existing service behavior unchanged, audit calls added after successful commits
- Grade history (`GradeHistoryModel`) continues to work alongside the new audit log system
- Audit log viewer uses collapsible `<details>` for JSON diff to keep the table compact

### Metrics
- 905 tests passing (886 + 19 new)
- Ruff check and format clean
- Database schema updated with `audit_logs` table

## P25 — Online Class Integration & Session Links (2026-09-01)

### Added
- `online_link` nullable column on `AcademyClassModel` — default online meeting link for all sessions in a class
- `online_link` nullable column on `SessionModel` — per-session link override (falls back to class default when empty)
- `online_link` field on `AcademyClass` and `Session` domain entities
- Class edit form: "لینک پیش‌فرض کلاس آنلاین" field (Admin + assigned Teacher)
- Session edit form: "لینک جلسه آنلاین" field (Admin + assigned Teacher) with hint about class default fallback
- Student timetable: "ورود به کلاس آنلاین" button for sessions happening today (within 30 minutes), using session link with class link fallback
- Teacher timetable: same "Join Online Class" button for their own classes
- Student class detail page: shows class online link when student is enrolled
- Admin class detail page: shows class online link
- Timetable entries: "آنلاین" badge on classes that have an online link
- In-app notification to enrolled students when a teacher/admin sets a session online link
- `class_edit` route now allows TEACHER role (with ownership check)
- `session_edit` route now allows TEACHER role (with ownership check)
- Database migration: `e5f6a7b8c9d0` adds `online_link` to `academy_classes` and `sessions`
- 17 new tests: class/session online_link CRUD, session override of class default, timetable data, upcoming sessions, enrollment visibility

### Design Decisions
- Session-level link overrides class-level link (fallback: `session.online_link or class.online_link`)
- "Join Class" button shown only when session is scheduled for TODAY and current time is within the session window (up to 30 minutes before start)
- Teacher access restricted to own classes only (ownership check via `teacher_user_id`)
- Online link stored as plain URL string (no video conferencing integration)
- Empty string cleared to `None` on save for clean nullable semantics

## P24 — Teacher Salaries & Payroll Management (2026-09-01)

### Added
- `TeacherContract` domain entity and `TeacherContractModel` — defines payment terms for teachers per class (PER_SESSION or PERCENTAGE_OF_REVENUE)
- `TeacherPayment` domain entity and `TeacherPaymentModel` — records finalized payouts with status (PENDING, PAID), deductions, and period dates
- `PaymentType` enum: PER_SESSION, PERCENTAGE_OF_REVENUE
- `PayrollStatus` enum: PENDING, PAID
- Payroll calculation service: `calculate_teacher_payroll()` — computes gross amount based on completed sessions and active contracts
- PERCENTAGE_OF_REVENUE logic: based on collected tuition (PAYMENT transactions with category=TUITION) in the period, not total charges
- Contract-specific fallback: class-specific contracts take priority over generic (class_id=None) contracts
- Contract CRUD: `create_contract`, `update_contract`, `delete_contract` (soft-delete), `list_contracts`, `get_contract`
- Payroll finalization: `finalize_payroll()` — creates TeacherPayment record with calculated amounts and deductions
- Payment status management: `mark_payment_paid()` — updates status to PAID with timestamp
- Teacher payroll summary: `list_teachers_with_payroll_summary()` — returns all teachers with calculated payroll for a period
- Admin routes: `/admin/contracts` (list, create, edit, delete), `/admin/payroll` (dashboard, finalize, mark paid)
- Admin UI templates: `contract_list.html`, `contract_form.html`, `payroll.html`
- Jalali month selector on payroll page with automatic Gregorian date range conversion
- Collapsible per-class breakdown on payroll page showing session counts and amounts
- Database migration: 2 new tables (teacher_contracts, teacher_payments)
- 41 new tests: Contract CRUD, PER_SESSION calculation, PERCENTAGE_OF_REVENUE calculation, non-completed session exclusion, finalization, payment status, admin UI routes, generic contract fallback, date range filtering

## P23 — Academic Calendar & Semester Management (2026-09-01)

### Added
- `AcademicYear` domain entity and `AcademicYearModel` — manages academic years (e.g., "1403-1404") with title, date range, and active flag
- `Semester` domain entity and `SemesterModel` — manages semesters within academic years with active flag
- `AcademicCalendarEvent` domain entity and `AcademicCalendarEventModel` — manages holidays/academic events with title, date range, recurring flag, and description
- `AcademicCalendarError` exception class for calendar operations
- Full CRUD service: `create_academic_year`, `update_academic_year`, `get_academic_year`, `list_academic_years`, `delete_academic_year`
- Full CRUD service: `create_semester`, `update_semester`, `get_semester`, `list_semesters`, `get_active_semester`, `delete_semester`
- Full CRUD service: `create_calendar_event`, `update_calendar_event`, `get_calendar_event`, `list_calendar_events`, `delete_calendar_event`
- `is_date_holiday(check_date)` — checks if a date falls within any calendar event
- `semester_id` foreign key on `AcademyClassModel` — links classes to semesters
- Active year/semester mutual exclusion — setting one as active deactivates others
- Smart session generation: `_generate_sessions` now skips dates falling within calendar events and extends schedule forward to find enough valid sessions
- `regenerate_sessions(academy_class)` — deletes future sessions without attendance, regenerates from the last preserved session forward, skipping holidays
- Session shifting (`shift_sessions_after_cancellation`) now also skips holidays
- Admin routes: `/admin/years` (CRUD), `/admin/semesters` (CRUD), `/admin/calendar` (CRUD)
- Admin route: `/admin/classes/<id>/regenerate-sessions` (POST) — safe session regeneration with confirmation
- Admin UI templates: `year_list.html`, `year_form.html`, `semester_list.html`, `semester_form.html`, `calendar_list.html`, `calendar_form.html`
- Semester filter on class list page (`/academy/classes?semester_id=X`)
- Semester dropdown on class creation form
- Semester display on class detail page
- "Regenerate Sessions" button on class detail page
- Sidebar links: "سال تحصیلی", "نیم‌سال‌ها", "تقویم آموزشی"
- Database migration: 3 new tables, 1 altered table (semester_id FK on academy_classes)
- 46 new tests: AcademicYear CRUD, Semester CRUD, CalendarEvent CRUD, holiday detection, session generation with holidays, session regeneration with attendance preservation, semester-class association, admin route authorization

### Changed
- `_generate_sessions()` — now checks `_is_date_holiday()` and skips holiday dates, extending schedule forward until enough valid sessions found
- `shift_sessions_after_cancellation()` — now checks `_is_date_holiday()` and skips holiday dates
- `create_class()` — accepts optional `semester_id` parameter
- `list_classes()` — accepts optional `semester_id` filter parameter
- Class list template — added semester filter dropdown
- Class creation form — added semester dropdown
- Class detail template — shows semester info and "Regenerate Sessions" button

### Metrics
- 828 tests passing
- Ruff check and format clean

## P22 — Public Enrollment Portal & Excel Power (2026-09-01)

### Added
- Excel import service (`excel_service.py`) in Application layer for bulk student import
- Admin route `/enrollment/admin/import/students` (GET/POST) for uploading .xlsx files
- Excel file parsing with validation: required columns (first_name, last_name, national_id, mobile_phone, birth_date), optional gender
- Duplicate detection by national_id — skips existing students and reports them
- Error handling: malformed dates, missing fields, blank rows gracefully handled
- Student import creates UserModel (inactive), assigns STUDENT role, creates StudentProfileModel, password = national_id
- Excel export routes for attendance, assessment, and finance reports (`/xlsx` endpoints)
- Export-to-Excel buttons alongside existing CSV buttons in reporting templates
- Public enrollment blueprint (`/enrollment/apply`) — no login required
- Public enrollment form: first_name, last_name, national_id, mobile_phone, birth_date (Jalali), gender, class dropdown
- Public enrollment creates inactive user + StudentProfileModel + PENDING EnrollmentModel
- Existing students linked to their application (no duplicate user creation)
- Standalone Persian RTL public page with custom header (no admin sidebar)
- Admin "Approve and Activate" button for public enrollments — activates user account, sets password, approves enrollment
- Public enrollment success page with password info
- Landing page "Online Enrollment" (ثبت‌نام آنلاین) button
- Import result page showing created/duplicates/errors per row
- 22 new tests: Excel parser (valid, duplicate, malformed, missing fields, blank rows), public enrollment form, approve-activate flow, import/upload routes

### Changed
- `requirements.txt` — added `openpyxl>=3.1,<4`
- Reporting CSV export routes now have parallel Excel export routes

### Metrics
- 782 tests passing
- Ruff check and format clean

## P21 — Advanced Grading & Transcripts (2026-08-31)

### Added
- `GradingTemplate` domain entity and model for defining weight distribution per class
- `GradingComponent` domain entity and model for mapping assessment types to weights
- Grading template CRUD functions: `create_grading_template()`, `update_grading_template()`, `get_grading_template()`, `get_class_grading_template()`
- `calculate_final_grade(enrollment_id)` — weighted grade calculation across assessment types
- Negative marking support: `penalty_factor` field on `AssessmentModel` (0-1 range)
- `wrong_count` field on `AssessmentResultModel` for negative marking audit trail
- Effective score formula: `max(0, raw_score - (wrong_count * penalty_factor))`
- `get_transcript_data(enrollment_id)` — comprehensive transcript data service
- Grading template management route (`/assessment/admin/class/<class_id>/grading-template`)
- Printable transcript route (`/assessment/student/<enrollment_id>/transcript`)
- Print transcript button on student class results page
- Grading template link on admin class report page
- Wrong count inputs on teacher and admin grading forms (when penalty_factor > 0)
- Grading template form with dynamic component rows and real-time weight validation
- Printable transcript template with A4-friendly `@media print` CSS
- 23 new tests for grading templates, weighted grades, negative marking, and transcripts

### Changed
- `create_assessment()` now accepts `penalty_factor` parameter (default 0)
- `record_result()` now accepts `wrong_count` parameter and applies negative marking
- `record_bulk_results()` now passes `wrong_count` to `record_result()`
- Teacher and admin grading forms show wrong count column when assessment has penalty_factor > 0
- Assessment create form includes penalty_factor input field

### Database
- New table: `grading_templates` (id, class_id, title, created_at, updated_at)
- New table: `grading_components` (id, template_id, assessment_type, weight)
- Altered table: `assessments` — added `penalty_factor` column (NUMERIC(4,2), default 0)
- Altered table: `assessment_results` — added `wrong_count` column (INTEGER, nullable)
- Migration: `a2b3c4d5e6f7_add_grading_templates_and_negative_marking`

## P19 — Payment Receipts, Notifications & Admin Visibility (2026-08-31)

### Added
- Payment receipt generation route (`/finance/receipt/<transaction_id>`)
- Printable receipt template with Vazirmatn font, academy name, student name, Jalali date, amount, tracking number, payment method, and status
- Print-friendly CSS (`@media print`) that hides sidebars and headers
- "Print Receipt" (چاپ رسید) button on admin transaction detail page
- "Receipt" (رسید) button on each transaction row in student finance and parent child statement pages
- In-app payment confirmation notification triggered automatically on successful online payment (PAYMENT_RECEIVED type)
- Notification message includes amount and tracking number in Persian
- Graceful degradation if notification providers are unavailable
- Admin finance dashboard stat card: "Online Payments Today" (پرداخت‌های آنلاین امروز) with count and total amount
- Payment method filter (روش پرداخت) on admin transaction list (Online, Cash, Card, Bank Transfer, Other)
- Persian labels for payment methods in filter dropdown

### Changed
- `get_dashboard_summary()` now includes `today_online_payments_count` and `today_online_payments_amount`
- Admin transaction detail page now shows receipt print button unconditionally (not only for ACTIVE transactions)
- Student and parent finance tables now include an "Operations" column with receipt links

## P18 — ZarinPal Online Payment Integration (2026-08-31)

### Added
- PaymentGateway abstraction (ABC) with PaymentRequestResult/PaymentVerificationResult dataclasses
- ZarinPal v4 REST API implementation with sandbox/production modes
- NullPaymentGateway fallback when no gateway configured
- Payment service: initiate_online_payment (creates PENDING transaction, returns redirect URL)
- Payment service: process_payment_callback (verifies with ZarinPal, updates transaction to ACTIVE/FAILED)
- Student online payment route (`/finance/student/pay`)
- Parent online payment route (`/finance/parent/child/<id>/pay`)
- Payment callback route (`/finance/payment/callback`) — no login required (external redirect)
- Age-based access control for student finance (18+ only)
- Configuration: ZARINPAL_MERCHANT_ID, ZARINPAL_SANDBOX environment variables
- 15 new tests covering payment initiation, callback processing, gateway integration, authorization

### Design Decisions
- PENDING transactions do not affect student balance until verified (ACTIVE)
- Callback route is public (no login) since ZarinPal redirects externally
- Transaction lookup by authority code (reference_number) for callback processing
- Sandbox mode enabled by default for development safety

## P17 — Final MVP Polish & Hardening (2026-08-31)

### Added
- Auth services: create_teacher_user, create_parent_user, create_admin_user, update_user_profile, link_parent_student, unlink_parent_student, get_user_profile_data, list_users
- Admin user management blueprint (`/admin/users`, `/admin/users/create`, `/admin/users/<id>/edit`)
- Admin user list with search, role filter, and pagination
- Admin user create form with role-based conditional profile fields (JavaScript toggle)
- Admin user edit page: profile editing, password reset, toggle active/inactive
- Parent-student linking UI in admin edit page (link and unlink)
- `flask seed` CLI command (creates roles, 4 test users, links parent1 to student1)
- Seed command is idempotent (safe to run multiple times)
- Sidebar link to admin user management
- 35 new tests: auth services, seed CLI, admin routes, parent-student linking UI

### Fixed
- Template nesting bug in user_edit.html (unclosed `{% if profile %}` block)
- Seed command bug (`StudentProfileModel.query.filter_by(login=...)` — incorrect field)

### Changed
- `parent_user` test fixture now creates a `ParentProfileModel` for proper admin UI testing

### Metrics
- 691 tests passing
- Ruff check and format clean

## P14 — Calendar, User Profiles & MVP Data UX (2026-08-31)

### Added
- Centralized Persian date system: parse_jalali_date, format_jalali_date_input, parse_jalali_date_or_none
- `to_jalali_input` template filter for form inputs
- SessionEditHistoryModel for tracking session date/time/title changes
- Profile photo upload integration with StoredFile + StorageBackend
- 58 new tests for calendar, profile, session editing, finance labels, landing page

### Changed
- Class creation form uses Jalali date text inputs instead of HTML date type
- Session edit/reschedule forms use Jalali date inputs
- Session detail/list display Jalali dates
- Class status dropdown shows Persian labels
- Student profile page: Jalali birth_date input, profile photo section
- Finance templates: all category/payment_method fields use |persian_label
- Landing page redesigned: 6 feature cards, responsive, professional
- Auth/academy flash messages translated to Persian
- Session edit records history with editor reference
- Session edit preserves attendance records

### Fixed
- Broken HTML in session_detail.html, session_list.html, admin_transaction_detail.html
- Finance templates showing raw English enum values (category, payment_method)
- Optional end_date parsing on class creation (was raising ValueError on empty)

### Migration
- Added session_edit_history table (eb6087341015)

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

- Established project roadmap (P0 through P13) and updated project status to P1 — Identity & Access

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

## P9 — Notifications (2026-08-30)

### Added

- Notification domain entity with enums (NotificationChannel, NotificationStatus, NotificationPriority, NotificationType, DeliveryStatus, ReadStatus)
- NotificationTemplate domain entity with variable rendering
- NotificationPreference domain entity for per-user channel/type preferences
- NotificationDelivery domain entity for multi-channel delivery tracking
- InAppNotification domain entity for internal notifications
- Notification database model with indexes and relationships
- NotificationDelivery database model with unique constraint (notification_id, channel)
- NotificationTemplate database model with active/inactive support
- NotificationPreference database model with unique constraint (user_id, type, channel)
- InAppNotification database model with read/unread status
- Provider abstraction (NotificationProvider ABC with send, validate_recipient, is_available)
- SMS provider with environment-based configuration
- Telegram Bot API provider with environment-based configuration
- Bale Bot API provider with environment-based configuration
- Email/SMTP provider with environment-based configuration
- Provider registry for channel-to-provider resolution
- Graceful handling of missing provider credentials (application does not fail at startup)
- Notification application service (create, send, cancel, retry, list, count)
- Multi-channel notification delivery (IN_APP, SMS, TELEGRAM, BALE, EMAIL)
- Manual notification sending by admin
- Announcement system (multi-user, multi-channel)
- Notification template system (CRUD, rendering with variables, active/inactive)
- User notification preferences (enable/disable per type per channel)
- Mandatory notification bypass (WELCOME, PASSWORD_CHANGED ignore preferences)
- In-app notification system (unread/read, mark as read, mark all as read)
- Event handlers for enrollment, session, activity, assessment, finance, and account events
- Admin notification dashboard with filters, pagination, and provider health status
- Admin notification detail with delivery records
- Admin manual notification interface
- Admin announcement interface
- Admin template management (create, edit, delete)
- Student notification list with read/unread status
- User notification preferences UI
- Navigation links for notifications across all roles
- 68 tests covering domain entities, providers, templates, services, in-app, preferences, event handlers, multi-channel, authorization, and routes

### Design Decisions

- Notification domain is independent of any specific delivery provider
- Provider-specific code is isolated in infrastructure layer
- Multi-channel delivery uses independent delivery records per channel
- In-app notifications do not require external provider configuration
- Mandatory notifications (WELCOME, PASSWORD_CHANGED) bypass user preferences
- Event-driven architecture for loose coupling with existing services
- Missing provider credentials do not break application startup
- Provider abstraction allows future provider additions without domain changes

## P10 — Reporting & Analytics (2026-08-30)

### Added

- Reporting application service with centralized dashboard overview
- Student comprehensive report (profile, enrollments, attendance, activities, assessments, finance)
- Class comprehensive report (enrollments, sessions, attendance, activities, assessments, finance)
- Course comprehensive report (classes, enrollments, activities)
- Attendance reports with filters (class, student, date range)
- Attendance alerts (low attendance detection with configurable threshold)
- Assessment reports (scores, averages, pass rates, distribution)
- Activity/homework reports (completion rates, late submissions, grades)
- Finance reports (revenue, debt, payments, discounts, refunds)
- Enrollment reports (status counts, approval rates, filters)
- Teacher reports (classes, students, sessions, activities, assessments)
- Operational reports (today's classes, pending requests, attention items)
- Notification reports (delivery stats, channel success rates)
- CSV export (attendance, assessment, finance)
- Authorization enforcement (Admin full, Teacher own classes, Student own, Parent linked children)
- 17 report templates with Persian RTL UI
- Navigation links for all roles (Admin, Teacher, Student, Parent)
- 35 tests covering reporting services, authorization, filters, and edge cases

### Design Decisions

- Centralized ReportingService queries cross-cutting data without duplicating domain logic
- Role-based access enforced at service level (Admin sees all, Teacher sees own classes, Student sees own data, Parent sees linked children)
- Report routes organized by domain area (admin, student, class, course, attendance, assessment, activity, finance, enrollment, teacher, operational, notification)
- CSV export available for attendance, assessment, and finance data
- Reports use existing domain services for data access (no direct queries bypassing business logic)

## P11 — File & Document Management (2026-08-30)

### Added

- Centralized file management module with clean architecture
- Domain entities: StoredFile, FileStatus, FileVisibility, FileCategory
- Storage abstraction (StorageBackend ABC) with LocalStorageBackend
- File validation (extension allowlist, MIME type, configurable size limits)
- Secure filename generation (UUID-based keys, path traversal prevention)
- File upload, download, soft/hard delete, replace services
- Generic entity association (entity_type + entity_id) for multi-module use
- Authorization enforcement (Admin full access, Owner access, Public visibility)
- Admin file management (list, search, filter by category/status/uploader, detail, delete)
- Orphan file detection (files without entity or storage)
- Reusable file upload UI component
- API endpoints for file metadata and deletion
- Configuration (FILE_STORAGE_BACKEND, FILE_STORAGE_PATH, FILE_MAX_UPLOAD_SIZE)
- .env.example updated with file management configuration
- 80 tests covering domain, storage, validation, service, authorization, routes, and security

### Design Decisions

- Storage abstraction allows future S3/object storage replacement without changing application code
- Generic entity association (entity_type + entity_id) avoids separate file tables per module
- Soft deletion preserves metadata history while preventing access to deleted files
- UUID-based storage keys prevent filename collisions and path traversal attacks
- Existing ActivityFileModel preserved for backward compatibility
- File categories are string-based for extensibility without migrations

## P12 — UI/UX, Frontend & User Experience Overhaul (2026-08-31)

### Added

- CSS architecture: 9 modular CSS files (tokens, base, layout, components, forms, tables, dashboard, utilities, responsive)
- Design token system (CSS custom properties for colors, spacing, typography, shadows, borders)
- Vazirmatn Persian web font loaded from Google Fonts CDN
- Inline SVG icon system (no icon library dependency)
- Base template redesign: sidebar + header app shell
- Sidebar persistent on desktop (>1024px), hamburger toggle on mobile/tablet
- Reusable component macros: page_header, empty_state, status_badge, stat_card, pagination, breadcrumbs, confirm_dialog
- Reusable form macros: form_field, form_select, form_textarea, form_checkbox, form_section
- Flash message component (shared across all pages via base.html inclusion)
- Error pages: 400, 403, 404, 500 with Persian UI and navigation
- Auth pages redesign (login, change_password, dashboard) with Persian UI
- Portal dashboards redesign (admin, teacher, student, parent)
- All module templates redesigned with new design system (88 templates total)
- Main.js rewrite: sidebar toggle, auto-dismiss alerts, toast notifications, button loading states, confirm dialogs
- All UI text in Persian, RTL layout, mobile-friendly responsive design

### Design Decisions

- CSS architecture uses 9 modular files for maintainability and clear separation of concerns
- Design tokens via CSS custom properties for easy theme customization
- Vazirmatn font chosen for Persian language support and modern design
- Inline SVG icons avoid external icon library dependencies
- Sidebar layout provides consistent navigation across all pages
- Component macros ensure consistent UI patterns across all templates
- Form macros provide standardized form layouts and validation states
- Error pages provide Persian UI with navigation back to dashboard
- All templates follow the same design system for visual consistency

## P13 — MVP Stabilization, Core UX Completion & Production-Grade Foundation (2026-08-31)

### Added

- Persian date infrastructure: `jdatetime` library, centralized `date_utils.py`, Jinja template filters (`jalali`, `jalali_datetime`, `jalali_time`, `to_jalali`, `currency`)
- User profile management: view/edit profile page at `/auth/profile`
- Homepage landing page with feature cards and login CTA
- CSRF protection via Flask-WTF on all 38+ POST forms
- Session editing: update title, description, date, time via `/academy/session/<id>/edit`
- Curriculum auto-numbering: syllabus order auto-suggested as next available
- Age eligibility check enforced during enrollment (student birth_date vs course age range)
- Seed script expansion: courses, classes, sessions, enrollment, attendance, activities, assessments, finance records
- 17 new regression tests (age restrictions, session editing, enrollment eligibility, syllabus numbering)

### Fixed

- Jinja `TemplateRuntimeError: No test named 'None'` (43 occurrences across 15 assessment templates — `is not None` → `is not none`)
- `update_session` `is_rescheduled` flag now correctly detects date changes
- `update_course` now correctly allows clearing age restrictions by passing `None`
- Raw English enum values in assessment, finance, notification, and file management templates replaced with `status_badge` macro
- English confirm dialog text replaced with Persian

### Changed

- All 28+ template files migrated from `strftime` to Jalali date filters
- Finance filter UI redesigned with proper form-card layout, consistent inputs, clear filter button
- All `status_badge` macro labels expanded: DEBTOR, CREDIT, LOCAL, PUBLIC, PRIVATE, YES, NO, INACTIVE
- Production config: SESSION_COOKIE_SECURE, SESSION_COOKIE_SAMESITE, PERMANENT_SESSION_LIFETIME
- TestingConfig: WTF_CSRF_ENABLED = False (test compatibility)

### Dependencies

- Added `jdatetime>=6,<7` (Persian/Jalali calendar)
- Added `Flask-WTF>=1.2,<2` (CSRF protection)

### Metrics

- 594 tests passing
- Ruff check and format clean
- Database migrations in sync
