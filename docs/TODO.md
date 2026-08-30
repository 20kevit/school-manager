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

- [ ] Advanced financial reports
- [ ] Advanced student reports
- [ ] Advanced attendance reports
- [ ] Teacher reports
- [ ] Advanced class reports
- [ ] Advanced analytics

## P11 — Administration

- [ ] System settings
- [ ] Profile management
- [ ] Data management
- [ ] Audit logs
- [ ] Backup / restore

## P12 — Future

- [ ] Mobile application
- [ ] Advanced permissions
- [ ] Advanced analytics
- [ ] AI features
- [ ] Multi-branch support
