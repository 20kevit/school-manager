# Roadmap

## P0 — Foundation

- [x] Project bootstrap
- [x] Git repository
- [x] Documentation foundation
- [x] Testing foundation

## P1 — Identity & Access

- [x] User
- [x] Roles
- [x] Student Profile
- [x] Teacher Profile
- [x] Parent Profile
- [x] Authentication
- [x] Authorization
- [x] Password management

## P2 — Academy Structure

- [x] Course
- [x] Course syllabus
- [x] Class
- [x] Class schedule
- [x] Session generation
- [x] Session rescheduling
- [x] Session cancellation

## P3 — Enrollment

- [x] Enrollment
- [x] Enrollment requests
- [x] Admin approval
- [x] Enrollment lifecycle

## P4 — Attendance

- [x] Attendance
- [x] Teacher attendance management
- [x] Attendance history
- [ ] Attendance reports

## P5 — Learning Activities

- [x] General Activity model
- [x] HOMEWORK as first activity type
- [x] Multiple activities per Session
- [x] Independent activities
- [x] Course default activities
- [x] Class-specific customization
- [x] Student submissions (text + files)
- [x] Submission history with versioning
- [x] Resubmission
- [x] Late submission handling
- [x] Required/optional activities
- [x] Teacher/Admin grading
- [x] Teacher feedback
- [x] RETURNED workflow
- [x] Activity deactivation preserves history
- [x] Admin, Teacher, Student authorization
- [x] Educational resources

## P6 — Finance

- [x] Financial ledger
- [x] Class tuition
- [x] Discounts
- [x] Partial payments
- [x] Credit / debt
- [x] Refunds
- [x] Payment history
- [x] Online payment gateway (ZarinPal)
- [x] Payment receipt generation (printable)
- [x] Payment notifications (in-app)
- [x] Admin online payment visibility

## P7 — Exams, Assessments & Grades

- [x] Assessment domain model (types, statuses)
- [x] Assessment CRUD (create, update, cancel, reschedule)
- [x] Final Exam support
- [x] Assessment scheduling (independent of sessions)
- [x] Assessment eligibility (enrollment-based)
- [x] AssessmentResult domain model
- [x] Numeric 0–100 grading
- [x] Configurable maximum score
- [x] Configurable passing score
- [x] Pass/fail calculation
- [x] Absent/Excused states
- [x] Grade history (corrections)
- [x] Teacher grading (authorized classes only)
- [x] Bulk grading
- [x] Admin grading
- [x] Student result view
- [x] Parent result view (linked children)
- [x] Class academic summary
- [x] Student academic summary
- [x] Assessment reports
- [x] CSV export
- [x] Server-side authorization
- [x] Database migration
- [x] Comprehensive tests

## P8 — Portals

- [x] Student dashboard
- [x] Parent dashboard
- [x] Teacher dashboard
- [x] Admin dashboard (production-quality redesign: verified role/status metrics, attention list, today/finance/trends sections — see docs/ADMIN_DASHBOARD.md)

## P9 — Notifications

- [x] Notification domain (entities, enums)
- [x] Provider abstraction (NotificationProvider ABC)
- [x] SMS provider implementation
- [x] Telegram Bot API provider
- [x] Bale Bot API provider
- [x] Email/SMTP provider
- [x] Provider registry and health status
- [x] Graceful missing credential handling
- [x] Notification application service
- [x] Multi-channel delivery
- [x] Manual notification sending
- [x] Announcement system
- [x] Template system (CRUD, rendering)
- [x] User notification preferences
- [x] Mandatory notification bypass
- [x] In-app notifications
- [x] Event handlers (enrollment, session, activity, assessment, finance, account)
- [x] Admin notification dashboard
- [x] Admin notification detail
- [x] Admin manual notification interface
- [x] Admin announcement interface
- [x] Admin template management
- [x] Student notification list
- [x] Teacher notification list
- [x] Parent notification list
- [x] User notification preferences UI
- [x] Navigation links
- [x] Database migration
- [x] 68 notification tests
- [x] Final lint, format, and verification

## P10 — Reports & Analytics

- [x] Reporting service with centralized dashboard overview
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
- [x] Authorization enforcement (Admin, Teacher, Student, Parent)
- [x] Persian RTL UI templates for all reports
- [x] Navigation links for all roles
- [x] 35 reporting tests

## P11 — File & Document Management

- [x] Centralized file management module
- [x] Domain entities (StoredFile, FileStatus, FileVisibility, FileCategory)
- [x] Storage abstraction (StorageBackend ABC)
- [x] LocalStorageBackend implementation
- [x] File validation (extension, MIME type, size)
- [x] Secure filename generation (path traversal prevention)
- [x] File upload service
- [x] File download with authorization
- [x] File soft/hard deletion
- [x] File replacement
- [x] File metadata and listing with pagination
- [x] Generic entity association (entity_type + entity_id)
- [x] Authorization enforcement (Admin, Owner, Public)
- [x] Admin file management interface (list, search, filter, detail, delete)
- [x] Orphan file detection
- [x] File upload component (reusable)
- [x] API endpoints (metadata, delete)
- [x] Configuration (FILE_STORAGE_*, FILE_MAX_UPLOAD_SIZE)
- [x] .env.example updated
- [x] 80 file management tests
- [x] Documentation updated

## P12 — UI/UX, Frontend & User Experience Overhaul

- [x] CSS architecture: 9 modular CSS files (tokens, base, layout, components, forms, tables, dashboard, utilities, responsive)
- [x] Base template redesign: sidebar + header app shell
- [x] Vazirmatn font, SVG icons, sidebar toggle
- [x] Reusable component macros (page_header, empty_state, status_badge, stat_card, pagination, breadcrumbs, confirm_dialog)
- [x] Reusable form macros (form_field, form_select, form_textarea, form_checkbox, form_section)
- [x] Flash message component
- [x] Error pages (400, 403, 404, 500) with Persian UI
- [x] Auth pages redesign (login, change_password, dashboard)
- [x] Portal dashboards redesign (admin, teacher, student, parent)
- [x] All module templates redesigned with new design system
- [x] 577 tests passing, Ruff clean

## P13 — MVP Stabilization, Core UX Completion & Production-Grade Foundation

- [x] Fix Jinja `is not None` template errors (43 instances across 15 files)
- [x] Course age restriction semantics (nullable min/max_age, validation)
- [x] Age eligibility check during enrollment
- [x] Curriculum auto-numbering (syllabus order)
- [x] Session editing (title, description, date, time)
- [x] Persian calendar infrastructure (jdatetime, Jalali filters)
- [x] All templates migrated to Jalali date filters
- [x] User profile management (view/edit)
- [x] Centralized Persian labels (100+ enum/status values)
- [x] Finance filter UX improvement
- [x] Homepage redesign (landing page)
- [x] CSRF protection (Flask-WTF)
- [x] Production security (session cookies, lifetime)
- [x] Seed script expansion
- [x] UX consistency audit (status_badge, Persian labels, raw English fixes)
- [x] Database migration integrity verified
- [x] 17 new regression tests (age, session editing, enrollment eligibility)
- [x] 594 tests passing, Ruff clean

## P14 — Calendar, User Profiles & MVP Data UX

- [x] Centralized Persian date system (parse/format/validate)
- [x] Class creation with Jalali date inputs
- [x] Session edit/reschedule with Jalali date inputs
- [x] Session edit history model and tracking (SessionEditHistoryModel)
- [x] Student profile management with Jalali birth_date
- [x] Profile photo upload integration (StoredFile + StorageBackend)
- [x] Finance template localization (category, payment_method Persian labels)
- [x] Landing page redesign (6 feature cards, responsive)
- [x] Auth/academy flash messages in Persian
- [x] Class status dropdown with Persian labels
- [x] Fixed broken HTML in session/finance templates
- [x] Session edit preserves attendance records
- [x] 58 new tests (calendar, profile, session, finance, landing page)
- [x] 652 tests passing, Ruff clean

## P15 — Bug Fixes & P11 File Integration

- [x] Fix session edit history bug (dedicated variables before mutation)
- [x] Refactor activity file upload/download to use P11 FileService
- [x] Translate activity flash messages to Persian
- [x] 4 new tests, 656 total tests passing

## P16 — Admin User Management & System Seeding

- [x] Admin user management services (create_teacher/parent/admin_user, update_profile, list_users)
- [x] Admin user list with search, role filter, pagination
- [x] Admin user create form with role-based profile fields
- [x] Admin user edit page (profile, password, toggle active)
- [x] Parent-student linking UI (link/unlink)
- [x] `flask seed` CLI command (idempotent)
- [x] 35 new tests, 691 total tests passing

## P21 — Advanced Grading & Transcripts

- [x] GradingTemplate domain entity and model
- [x] GradingComponent domain entity and model
- [x] Grading template CRUD (create, update, get)
- [x] Weighted grade calculation (calculate_final_grade)
- [x] Negative marking support (penalty_factor on AssessmentModel)
- [x] wrong_count field on AssessmentResultModel
- [x] Transcript data service (get_transcript_data)
- [x] Grading template management UI (admin)
- [x] Printable transcript template (A4-friendly)
- [x] Print buttons on student/parent views
- [x] Wrong count inputs on grading forms
- [x] Database migration
- [x] 23 new tests, 760 total tests passing

## P22 — Public Enrollment Portal & Excel Power

- [x] Excel import/export service (openpyxl)
- [x] Excel import: student data with duplicate detection
- [x] Admin Excel import route and UI
- [x] Excel export for attendance, assessment, finance reports
- [x] Public enrollment form (no login required)
- [x] Public form creates inactive user + PENDING enrollment
- [x] Existing student linking (no duplicate user)
- [x] Admin "Approve and Activate" for public enrollments
- [x] Landing page "Online Enrollment" button
- [x] 22 new tests, 782 total tests passing

## P23 — Academic Calendar & Semester Management

- [x] AcademicYear domain entity and model (CRUD)
- [x] Semester domain entity and model (CRUD, active flag, mutual exclusion)
- [x] AcademicCalendarEvent domain entity and model (CRUD, recurring flag)
- [x] `is_date_holiday()` — checks if a date falls within any calendar event
- [x] `semester_id` FK on AcademyClassModel
- [x] Smart session generation: skips holiday dates, extends schedule to fill gaps
- [x] Session shifting skips holidays
- [x] `regenerate_sessions()` — preserves past + attended sessions, regenerates forward
- [x] Admin routes: year, semester, calendar CRUD, regenerate sessions
- [x] Admin UI templates for all calendar management
- [x] Semester filter on class list
- [x] Semester dropdown on class form
- [x] Sidebar links for calendar management
- [x] Database migration (3 new tables, 1 altered)
- [x] 46 new tests, 828 total tests passing

## P24 — Teacher Salaries & Payroll Management

- [x] TeacherContract domain entity and model
- [x] TeacherPayment domain entity and model
- [x] Contract CRUD service
- [x] Payroll calculation service
- [x] Admin contract and payroll management routes
- [x] Admin UI templates for contracts and payroll
- [x] Database migration
- [x] 58 new tests, 886 total tests passing

## P25 — Online Class Integration & Session Links

- [x] `online_link` on AcademyClassModel and SessionModel
- [x] Class and session edit forms for online links
- [x] Student/teacher timetable "Join Online Class" button
- [x] In-app notification when session link is set
- [x] Database migration
- [x] 17 new tests, 886 total tests passing

## P26 — Automated Tasks & Audit Logging

- [x] Background scheduler (daemon thread)
- [x] Daily class reminder notifications
- [x] Weekly payment reminder notifications
- [x] CLI commands (`flask run-scheduler`, `flask run-jobs`)
- [x] AuditLog domain entity and AuditLogModel
- [x] AuditService (log, query, count)
- [x] Audit logging in assessment grade corrections
- [x] Audit logging in finance corrections and reversals
- [x] Admin audit log viewer with filters
- [x] 19 new tests, 905 total tests passing

## P27 — Deployment Readiness (Docker & Production Config)

- [x] Multi-stage Dockerfile (Python 3.12-slim, non-root user)
- [x] docker-compose.yml (PostgreSQL 15, Gunicorn, Nginx)
- [x] .dockerignore
- [x] wsgi.py Gunicorn entry point
- [x] gunicorn_config.py (workers, timeout, logging)
- [x] entrypoint.sh (DB wait, migrations, conditional seeding)
- [x] nginx/nginx.conf (reverse proxy, static files, gzip)
- [x] pool_pre_ping for PostgreSQL connection reliability
- [x] docs/DEPLOYMENT.md
- [x] 905 tests passing, Ruff check/format clean

## Demo — Isolated End-to-End Demo Environment

- [x] Demo database/role, checkout, venv, env file, systemd service (port 8101)
- [x] Nginx vhost + Let's Encrypt TLS for `demofca.20kevit.ir`
- [x] Deterministic/idempotent/guarded synthetic-academy generator
- [x] Scenario coverage across all modules, 12-month history
- [x] Demo credentials (shared `12345678`, hashed) and credential guide
- [x] Guard/reset/reconcile tests, full suite green, Ruff clean
- [x] Real-browser validation at 1440/768/390/320 with screenshots
- [x] Backup/recovery docs, production isolation verified
