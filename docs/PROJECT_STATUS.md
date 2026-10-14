# Project Status

**Current Phase:** Admin Dashboard Redesign — Completed
**Current Objective:** Production-quality administrator landing page with verified metrics.

**Previous Phase:** P27 — Deployment Readiness — Completed

**Previous Phase:** P26 — Automated Tasks & Audit Logging

## Status

Admin dashboard redesign (second iteration) is complete: whole-card clickable
KPIs with exact filtered destinations, server-rendered SVG charts (12-month
net/gross collections, requests vs approvals, 7-day attendance) with
data-table alternatives, grouped queries cutting dashboard queries ~40%
(76→46 on PostgreSQL), capacity attention, class status filter, 33+ dashboard
tests, full suite 1046 passed, Ruff clean, browser-validated at
1440/768/390/320 with zero overflow. See `docs/ADMIN_DASHBOARD.md`.

P27 is complete. The application is containerized with Docker, using Gunicorn as the production WSGI server, PostgreSQL 15 as the database, and Nginx as a reverse proxy. Entrypoint script handles migration and conditional seeding. All 905 tests pass.

## Completed

### P27 — Deployment Readiness (Docker & Production Config)
- [x] Multi-stage `Dockerfile` (Python 3.12-slim, non-root user, build stages)
- [x] `docker-compose.yml` with PostgreSQL 15, Gunicorn web service, Nginx reverse proxy
- [x] `.dockerignore` excluding dev artifacts
- [x] `wsgi.py` as dedicated Gunicorn entry point
- [x] `gunicorn_config.py` with configurable workers and 120s timeout
- [x] `entrypoint.sh` with DB wait, migration, and conditional seeding (`SEED_MODE`)
- [x] `nginx/nginx.conf` with reverse proxy, static files, gzip, upload limits
- [x] `pool_pre_ping=True` added to ProductionConfig for PostgreSQL reliability
- [x] `.env` with Docker-appropriate defaults
- [x] `docs/DEPLOYMENT.md` deployment guide
- [x] 905 tests passing, Ruff check/format clean

### P26 — Automated Tasks & Audit Logging
- [x] Lightweight background scheduler (`app/scheduler.py`) using daemon threads
- [x] Daily automated class reminder: in-app notifications for tomorrow's sessions
- [x] Weekly automated payment reminder: in-app notifications for students with outstanding debt
- [x] CLI commands: `flask run-scheduler` and `flask run-jobs`
- [x] `AuditLog` domain entity and `AuditLogModel` database table
- [x] `AuditService` with `log()`, `get_audit_logs()`, `count_audit_logs()`
- [x] Audit logging in `assessment_service.record_result()` and `update_result()`
- [x] Audit logging in `finance_service.correct_transaction()` and `reverse_transaction()`
- [x] Admin route `/admin/audit-logs` with filterable table
- [x] Admin sidebar link and audit log template
- [x] 19 new tests covering audit, scheduler, and admin routes
- [x] 905 total tests passing, Ruff check/format clean

### P25 — Online Class Integration & Session Links
- [x] `online_link` nullable column on `AcademyClassModel` — default class online meeting link
- [x] `online_link` nullable column on `SessionModel` — per-session link override
- [x] `online_link` field on `AcademyClass` and `Session` domain entities
- [x] Class edit form: "لینک پیش‌فرض کلاس آنلاین" field (Admin + assigned Teacher)
- [x] Session edit form: "لینک جلسه آنلاین" field (Admin + assigned Teacher) with fallback hint
- [x] Student timetable: "ورود به کلاس آنلاین" button for imminent sessions
- [x] Teacher timetable: same button for teacher's own classes
- [x] Student class detail: online link shown when enrolled
- [x] Admin class detail: online link displayed
- [x] Timetable badge: "آنلاین" tag on classes with online links
- [x] In-app notification to enrolled students when session online link is set
- [x] Teacher access restricted to own classes (ownership check)
- [x] Database migration: e5f6a7b8c9d0 (online_link on academy_classes, sessions)
- [x] 17 new tests: online_link CRUD, session override, timetable data, upcoming sessions
- [x] 886 total tests passing, Ruff check/format clean

### P24 — Teacher Salaries & Payroll Management
- [x] `TeacherContract` domain entity and `TeacherContractModel` — PER_SESSION or PERCENTAGE_OF_REVENUE contracts per class
- [x] `TeacherPayment` domain entity and `TeacherPaymentModel` — payout records with PENDING/PAID status
- [x] Contract CRUD service: create, update, soft-delete, list, get
- [x] Payroll calculation: completed sessions × rate (PER_SESSION) or collected tuition × percentage (PERCENTAGE_OF_REVENUE)
- [x] Collected tuition = sum of PAYMENT transactions with category=TUITION for the class in the period
- [x] Class-specific contract priority over generic (class_id=None) fallback
- [x] Finalize payroll: creates TeacherPayment with gross amount and deductions
- [x] Mark payment paid: updates status and paid_at timestamp
- [x] Teacher payroll summary: list all teachers with calculated amounts for a period
- [x] Admin UI: contract management (list, create, edit, deactivate)
- [x] Admin UI: payroll dashboard with Jalali month selector and per-class breakdown
- [x] Database migration: teacher_contracts, teacher_payments tables
- [x] 41 new tests: contract CRUD, mixed contract types, non-completed session exclusion, finalization, payment status, admin routes, generic contract fallback, date range filtering
- [x] 869 tests passing at completion, Ruff check/format clean

### P23 — Academic Calendar & Semester Management
- [x] `excel_service.py` — Application-layer service for Excel import/export using openpyxl
- [x] Excel import: reads .xlsx with columns first_name, last_name, national_id, mobile_phone, birth_date, gender
- [x] Duplicate detection by national_id — skips existing students
- [x] Error handling: malformed dates, missing fields, blank rows
- [x] Import creates inactive UserModel, STUDENT role, StudentProfileModel (password = national_id)
- [x] Admin route `/enrollment/admin/import/students` with upload form and result page
- [x] Excel export routes for attendance, assessment, and finance reports
- [x] Public enrollment blueprint at `/enrollment/apply` — no login required
- [x] Public form: first_name, last_name, national_id, mobile_phone, birth_date (Jalali), gender, class dropdown
- [x] Creates inactive user + StudentProfileModel + PENDING EnrollmentModel
- [x] Existing students linked (no duplicate user creation)
- [x] Standalone Persian RTL public page with custom header
- [x] Admin "Approve and Activate" button for public enrollments
- [x] Landing page "Online Enrollment" button
- [x] 22 new tests: Excel parser, public enrollment, approve-activate, import routes
- [x] 782 total tests passing, Ruff check/format clean

### P21 — Advanced Grading & Transcripts
- [x] `GradingTemplate` domain entity and model — defines weight distribution for assessment types per class
- [x] `GradingComponent` domain entity and model — maps assessment types to weight percentages
- [x] Grading template CRUD: `create_grading_template()`, `update_grading_template()`, `get_grading_template()`, `get_class_grading_template()`
- [x] Weight validation: weights must sum to exactly 100%, clear error messages
- [x] `calculate_final_grade(enrollment_id)` — computes weighted average across all assessment types
- [x] Missing results treated as 0 (unless excused, which is ignored for now)
- [x] Negative marking: `penalty_factor` field on `AssessmentModel` (0-1 range)
- [x] `wrong_count` field on `AssessmentResultModel` for audit trail
- [x] Effective score formula: `max(0, raw_score - (wrong_count * penalty_factor))`
- [x] Grading template management UI (admin) — dynamic form with real-time weight validation
- [x] Printable transcript template (`transcript.html`) — A4-friendly with `@media print`
- [x] Transcript route: `/assessment/student/<enrollment_id>/transcript`
- [x] Print buttons on student class results and admin class report pages
- [x] Wrong count inputs on teacher and admin grading forms (when penalty_factor > 0)
- [x] `get_transcript_data(enrollment_id)` — comprehensive transcript data service
- [x] Database migration: 2 new tables, 2 altered tables
- [x] 23 new tests: grading templates, weighted grades, negative marking, transcripts
- [x] 760 total tests passing, Ruff check/format clean

## Completed

### P20 — Timetable, Conflict Detection & Rich Demo Seeder
- [x] `has_schedule_conflict()` function in enrollment service — compares WeeklySchedule of new class against all APPROVED/PENDING enrollments
- [x] `_times_overlap()` helper for time range comparison
- [x] `get_schedule_conflict_details()` returns detailed conflict info for admin warnings
- [x] Student self-enrollment blocked with Persian error message when schedule conflicts detected
- [x] Admin enrollment shows conflict warning with override option (force enrollment)
- [x] Student class detail page shows conflict warning before enrollment request
- [x] Student timetable route (`/portal/student/timetable`) — weekly grid Saturday-Friday
- [x] Teacher timetable route (`/portal/teacher/timetable`) — weekly grid for assigned classes
- [x] Timetable template with color-coded classes, clickable entries, Persian RTL, responsive design
- [x] Sidebar links to timetable for both student and teacher roles
- [x] `flask seed-demo` CLI command — generates admin, 3 teachers, 30 students, 5 parents
- [x] 4 courses with 5 classes (including intentional schedule conflicts for testing)
- [x] Random enrollments (approved + pending), past sessions, attendance records
- [x] Activities with submissions and grades, assessments with bulk grading results
- [x] Financial transactions (tuition charges, payments, partial payments, discounts)
- [x] 13 new tests for schedule conflict detection (overlap logic, edge cases, integration)
- [x] All 737 tests pass, Ruff check/format clean

### P19 — Payment Receipts, Notifications & Admin Visibility
- [x] Payment receipt route (`/finance/receipt/<transaction_id>`) with authorization checks
- [x] Printable receipt template (academy name, student name, Jalali date, amount, ref_id, payment method, status)
- [x] Print-friendly CSS (`@media print`) hiding sidebars/headers
- [x] Print receipt buttons on admin transaction detail, student finance, and parent child statement pages
- [x] In-app notification on successful online payment (PAYMENT_RECEIVED type)
- [x] Notification includes amount and tracking number in Persian
- [x] Graceful degradation if notification system unavailable
- [x] Admin dashboard: "Online Payments Today" stat card (count + total amount)
- [x] Payment method filter on admin transaction list
- [x] All tests pass, Ruff check/format clean

### P18 — ZarinPal Online Payment Integration
- [x] PaymentGateway abstraction (ABC) with result dataclasses
- [x] ZarinPal v4 REST API implementation (sandbox/production)
- [x] NullPaymentGateway fallback
- [x] Online payment initiation (PENDING transaction)
- [x] Payment callback processing (verification + status update)
- [x] Student and parent online payment routes
- [x] Payment callback route (public, no login required)
- [x] Configuration: ZARINPAL_MERCHANT_ID, ZARINPAL_SANDBOX
- [x] 15 new tests for payment services and routes

### P17 — Final MVP Polish & Hardening
- [x] Enhanced `flask seed` CLI command with realistic test data (course, class, sessions, enrollment, activity, assessment, finance)
- [x] UI audit: fixed 12+ raw English enum values in templates to use `|persian_label` filter
- [x] UI audit: fixed 18 date displays to use `|jalali` filter instead of raw ISO dates
- [x] UI audit: fixed 8 raw enum fallback branches in assessment templates
- [x] Authorization: added enrollment check to student activity submit POST route
- [x] Authorization: added enrollment check to student submission history GET route
- [x] All 691 tests pass, Ruff check/format clean
- [x] Auth services: create_teacher_user, create_parent_user, create_admin_user, update_user_profile, link_parent_student, unlink_parent_student, get_user_profile_data, list_users
- [x] Admin user list with search, role filter, pagination
- [x] Admin user create form with role-based conditional profile fields (JS toggle)
- [x] Admin user edit page: profile editing, password reset, toggle active/inactive
- [x] Parent-student linking UI in admin edit page (link/unlink)
- [x] `flask seed` CLI command (roles, 4 test users, parent-student link)
- [x] Seed command idempotent (safe to run multiple times)
- [x] Sidebar link to admin user management
- [x] 35 new tests: auth services, seed CLI, admin routes, parent-student linking
- [x] 691 total tests passing, Ruff check/format clean

## Completed

### P14 — Calendar, User Profiles & MVP Data UX
- [x] Centralized Persian date system: parse_jalali_date, format_jalali_date_input, parse_jalali_date_or_none
- [x] to_jalali_input template filter for form inputs
- [x] Class creation form uses Jalali date inputs (text, not type="date")
- [x] Session edit/reschedule forms use Jalali date inputs
- [x] Session detail/list display Jalali dates via |jalali filter
- [x] Class status dropdown shows Persian labels instead of raw English
- [x] SessionEditHistoryModel: tracks date/time/title changes with change_type (EDIT/RESCHEDULE)
- [x] update_session records edit history with editor reference
- [x] Student profile: Jalali birth_date input, profile photo upload/replace
- [x] Profile photo uses StoredFile + StorageBackend (P11 integration)
- [x] Profile page shows role info, read-only national_id and username
- [x] Finance templates: all category/payment_method fields use |persian_label
- [x] Fixed broken HTML in session_detail.html, session_list.html, admin_transaction_detail.html
- [x] Landing page redesigned: 6 feature cards, responsive, professional design
- [x] Auth flash messages translated to Persian
- [x] Academy flash messages translated to Persian
- [x] Session edit history preserves attendance records
- [x] SessionEditHistory migration created and applied
- [x] 58 new tests for calendar, profile, session editing, finance labels, landing page
- [x] 656 total tests passing, Ruff check/format clean

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

### P5 — Learning Activities & Homework
- [x] Activity domain entity with enums (ActivityType, ActivityRequirement, SubmissionStatus)
- [x] Activity database model with multi-level scope (Course, Class, Session)
- [x] ActivitySubmission model with versioned submission history
- [x] ActivityFile model for file upload tracking
- [x] Activity application service (CRUD, submission, grading, files)
- [x] Course → Class activity copying (persisted, not inherited)
- [x] Class-level activity customization independent of Course defaults
- [x] Multiple activities per Session
- [x] Independent activities (no session required)
- [x] Student submission with text content and file uploads
- [x] Versioned submission history (each attempt creates new version)
- [x] Late submission detection (accepts, marks as LATE)
- [x] Teacher/Admin grading with score, feedback, timestamps
- [x] RETURNED workflow for resubmission
- [x] File upload validation (type, size, MIME type)
- [x] Activity deactivation (soft-disable, preserves submissions)
- [x] Admin web UI: activity management, submissions, grading
- [x] Teacher web UI: my classes, activities, submissions, grading
- [x] Student web UI: my classes, activities, submit, history, feedback
- [x] File download with authorization
- [x] Database migration for activity models
- [x] 248 tests passing

### P6 — Finance & Tuition
- [x] FinancialTransaction domain entity with enums (TransactionType, TransactionCategory, PaymentMethod, TransactionStatus)
- [x] FinancialTransaction database model with indexes and relationships
- [x] Tuition field added to AcademyClass model (Numeric 12,2)
- [x] Finance application service (charges, payments, refunds, discounts, adjustments, corrections, reversals)
- [x] Balance derived from transactions (not mutable balance field)
- [x] Transaction history with signed amounts (PAYMENT/DISCOUNT positive, CHARGE/REFUND negated)
- [x] Correction mechanism (mark original as CORRECTED, create new corrected entry)
- [x] Reversal mechanism (keep original ACTIVE, create REVERSAL with opposite sign)
- [x] Enrollment integration (approval → tuition charge, cancellation → reversal)
- [x] Idempotent tuition charge (duplicate prevention per enrollment)
- [x] Tuition snapshot preserved at enrollment time
- [x] Class financial summary (total tuition, enrolled count, collections, outstanding)
- [x] Student balance, balance by class, statement, reports
- [x] Debt report, credit report, revenue report, dashboard summary
- [x] Transaction report with filters
- [x] Admin web UI: dashboard, transactions, create, detail, student statement, class financial, reports
- [x] Parent web UI: overview, child statement (limited to linked children)
- [x] Student web UI: my-finance (18+ check enforced)
- [x] Role-based access control (Admin full, Parent limited, Student 18+)
- [x] ZarinPal prepared architecturally (not implemented)
- [x] Database migration for finance models
- [x] 70 tests covering finance domain, services, enrollment integration, authorization, reports, and routes

### P7 — Exams, Assessments & Grades
- [x] Assessment domain entity with enums (AssessmentType, AssessmentStatus)
- [x] AssessmentResult domain entity with enums (ResultStatus, PresenceStatus, PassFailStatus)
- [x] GradeHistory domain entity for grade correction
- [x] Assessment database model with class relationship and indexes
- [x] AssessmentResult database model with unique constraint (assessment_id, enrollment_id)
- [x] GradeHistory database model with indexes
- [x] Assessment application service with CRUD, status transitions, results, bulk grading, history, reports, CSV export
- [x] Configurable maximum score per assessment
- [x] Configurable passing score per assessment
- [x] Pass/fail calculation from score and passing threshold
- [x] Absent/Excused presence states
- [x] Grade correction history with previous/new scores and metadata
- [x] Teacher authorization (assigned classes only)
- [x] Admin full access
- [x] Student result view (own results only)
- [x] Parent result view (linked children only)
- [x] Bulk grading for entire assessments
- [x] Class academic summary report
- [x] Student academic summary report
- [x] Assessment report (scores, averages, pass rates, etc.)
- [x] CSV export for assessment and student results
- [x] Historical results preserved on enrollment cancellation
- [x] Assessment scheduling independent of sessions
- [x] Server-side authorization enforcement
- [x] Admin web UI: assessment list, create, edit, detail, grading, reports, CSV export
- [x] Teacher web UI: my classes, class assessments, grading, grade history
- [x] Student web UI: my assessments, class results, result detail, CSV export
- [x] Parent web UI: children overview, child results, result detail
- [x] Navigation links for assessment management
- [x] Database migration for assessment models
- [x] 76 tests covering assessment CRUD, eligibility, results, bulk grading, grade history, authorization, reports, CSV export, domain entities, and integration
- [x] 394 total tests passing (P1-P7)

### P8 — Portals (Dashboards)
- [x] Portal module with role-specific dashboards
- [x] Student dashboard: enrolled classes, academic summary, attendance summary, financial balance (18+), recent results
- [x] Parent dashboard: children overview, per-child academic/attendance/finance summaries
- [x] Teacher dashboard: assigned classes, class summaries, pending grading counts
- [x] Admin dashboard: quick stats, pending enrollments, financial summary, recent classes
- [x] Portal service aggregating data from enrollment, assessment, attendance, finance, and academy modules
- [x] Portal blueprint registered and integrated
- [x] Main dashboard redirect to role-specific portal
- [x] 4 role-specific templates with Persian RTL UI
- [x] 394 total tests passing (P1-P8)

### P9 — Notifications
- [x] Notification domain with enums (Channel, Status, Priority, Type, DeliveryStatus, ReadStatus)
- [x] NotificationTemplate domain with variable rendering
- [x] NotificationPreference domain for per-user settings
- [x] NotificationDelivery domain for multi-channel tracking
- [x] InAppNotification domain for internal notifications
- [x] Provider abstraction (NotificationProvider ABC)
- [x] SMS provider (generic, environment-configured)
- [x] Telegram Bot API provider
- [x] Bale Bot API provider
- [x] Email/SMTP provider
- [x] Provider registry with health status
- [x] Graceful handling of missing provider credentials
- [x] Notification application service (create, send, cancel, retry, list, count)
- [x] Multi-channel delivery (IN_APP, SMS, TELEGRAM, BALE, EMAIL)
- [x] Manual notification sending by admin
- [x] Announcement system (multi-user, multi-channel)
- [x] Template system (CRUD, rendering, active/inactive)
- [x] User notification preferences (enable/disable per type per channel)
- [x] Mandatory notification bypass (WELCOME, PASSWORD_CHANGED)
- [x] In-app notifications (unread/read, mark as read, mark all as read)
- [x] Event handlers for enrollment, session, activity, assessment, finance, account events
- [x] Admin notification dashboard with filters and pagination
- [x] Admin notification detail with delivery records
- [x] Admin manual notification and announcement interfaces
- [x] Admin template management (create, edit, delete)
- [x] Student/Parent/Teacher notification list and preferences
- [x] Navigation links for notifications
- [x] Database migration for notification models
- [x] 68 new tests covering domain, providers, templates, services, in-app, preferences, events, multi-channel, authorization, and routes
- [x] 462 total tests passing (P1-P9)

### P10 — Reporting & Analytics
- [x] Reporting application service with centralized dashboard overview
- [x] Student comprehensive report (profile, enrollments, attendance, activities, assessments, finance)
- [x] Class comprehensive report (enrollments, sessions, attendance, activities, assessments, finance)
- [x] Course comprehensive report (classes, enrollments, activities)
- [x] Attendance reports with filters (class, student, date range)
- [x] Attendance alerts (low attendance detection with configurable threshold)
- [x] Assessment reports (scores, averages, pass rates, distribution)
- [x] Activity/homework reports (completion rates, late submissions, grades)
- [x] Finance reports (revenue, debt, payments, discounts, refunds)
- [x] Enrollment reports (status counts, approval rates, filters)
- [x] Teacher reports (classes, students, sessions, activities, assessments)
- [x] Operational reports (today's classes, pending requests, attention items)
- [x] Notification reports (delivery stats, channel success rates)
- [x] CSV export (attendance, assessment, finance)
- [x] Authorization enforcement (Admin full, Teacher own classes, Student own, Parent linked children)
- [x] Reporting blueprint registered and integrated
- [x] 12 report templates with Persian RTL UI
- [x] Navigation links for all roles
- [x] 35 tests covering reporting services, authorization, filters, and edge cases
- [x] 532 total tests passing (P1-P10)

### P11 — File & Document Management
- [x] Centralized file management module with domain entities
- [x] Storage abstraction (StorageBackend ABC) with LocalStorageBackend
- [x] File validation (extension allowlist, MIME type, size limits)
- [x] Secure filename generation (path traversal prevention, UUID-based keys)
- [x] File upload, download, delete (soft/hard), replace services
- [x] Generic entity association (entity_type + entity_id for multi-module use)
- [x] Authorization enforcement (Admin full, Owner access, Public visibility)
- [x] Admin file management (list, search, filter, detail, delete, orphan detection)
- [x] File upload UI component (reusable)
- [x] API endpoints (metadata, delete)
- [x] Configuration (FILE_STORAGE_BACKEND, FILE_STORAGE_PATH, FILE_MAX_UPLOAD_SIZE)
- [x] .env.example updated
- [x] 80 file management tests (domain, storage, validation, service, authorization, routes, security)
- [x] 577 total tests passing (P1-P12)

### P12 — UI/UX, Frontend & User Experience Overhaul
- [x] CSS architecture: 9 modular CSS files (tokens, base, layout, components, forms, tables, dashboard, utilities, responsive)
- [x] Vazirmatn web font loading, inline SVG icons
- [x] Base template redesign: sidebar + header app shell
- [x] Sidebar persistent on desktop, hamburger toggle on mobile/tablet
- [x] Reusable component macros (page_header, empty_state, status_badge, stat_card, pagination, breadcrumbs, confirm_dialog)
- [x] Reusable form macros (form_field, form_select, form_textarea, form_checkbox, form_section)
- [x] Flash message component (shared across all pages)
- [x] Error pages: 400, 403, 404, 500 with Persian UI
- [x] Auth pages redesign (login, change_password, dashboard)
- [x] Portal dashboards redesign (admin, teacher, student, parent)
- [x] All module templates redesigned: academy, activity, assessment, attendance, enrollment, finance, file_management, notification, reporting
- [x] Main.js rewrite: sidebar toggle, auto-dismiss alerts, toast system, button loading, confirm dialogs
- [x] All UI text in Persian, RTL layout
- [x] 577 tests passing, Ruff check/format clean
