# Changelog

All notable project-level changes are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

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
