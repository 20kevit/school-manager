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
- [ ] Payment receipt upload
- [ ] Future payment gateway integration

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
- [x] Admin dashboard

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

## P15 — Future

- [ ] Mobile application
- [ ] Advanced permissions
- [ ] Advanced analytics
- [ ] AI features
- [ ] Multi-branch support
- [ ] Payment gateway integration (ZarinPal)
- [ ] Payment receipt upload
- [ ] Attendance reports
- [ ] Parent-student link UI
- [ ] Academic calendar & holidays
