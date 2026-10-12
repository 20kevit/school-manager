# MVP Acceptance Checklist

Evidence-based status of the MVP workflows as of 2026-10-12 (code at `main`,
full suite **974 passed / 0 failed**, ruff clean, migrations verified to head
on fresh PostgreSQL). Items marked *manual* still need human/browser, external
credentials, or production rollout verification.

## Automated (pytest, SQLite) — verified

| # | Workflow | Evidence |
|---|---|---|
| 1 | Auth, logout, sessions, role boundaries | `test_auth.py` (incl. new rotation/throttle/secret tests), `test_authorization.py`, `test_roles.py` pass; live timetable routes 302→login |
| 2 | Admin/teacher/student/parent portals | Route tests + `any()`/`all()` Jinja globals present; transcript matrix (10 tests) |
| 3 | Public enrollment → approval → activation → forced password rotation | `test_enrollment.py` + new rotation-flow tests; approval preserves active accounts |
| 4 | Student/teacher records | `test_profiles.py`, `test_user.py` pass |
| 5 | Course/class assignment, enrollment | `test_courses.py`, `test_classes.py`, `test_enrollment.py` pass |
| 6 | Schedule generation, session regeneration | `test_phase23.py` green incl. date-relative regeneration tests |
| 7 | Attendance recording + reports | `test_attendance.py` pass |
| 8 | Assessments, grades, transcripts, teacher scoping | `test_assessment.py` (incl. 10 IDOR tests), `test_phase14.py` pass |
| 9 | Invoices, payments, online flow (mocked), refunds, balances | `test_finance.py`, `test_payment.py` pass incl. idempotency/cap tests |
| 10 | Payroll calc + finalization | `test_phase24.py` pass incl. channel/unique/deduction tests |
| 11 | In-app notifications, events | `test_notification.py` pass incl. handler-delivery/dedup tests |
| 12 | Uploads/downloads/visibility | `test_file_management.py` pass incl. 14 authz tests |
| 13 | Persian RTL, Jalali dates | Live login page renders RTL Persian title; Jalali utils covered in suite |
| 14 | Validation errors, empty states, 403/404 paths | Covered across route tests (400/401/403/404/429 assertions) |
| 16 | Migrations, startup, health | Fresh-PG upgrade to head verified; `SECRET_KEY` guard tests; live 200s |

## Manual / external — not yet verified

| # | Item | Blocker / note |
|---|---|---|
| 3b | Real SMS/OTP onboarding | No provider integration; SMS honestly reports unavailable |
| 9b | Live ZarinPal charge + callback | Needs merchant credentials + sandbox run; code path tested with mocks only |
| 11b | Telegram/Bale delivery | Tokens unconfigured; in-app channel verified |
| 15 | Mobile viewport usability | Requires browser testing; templates are responsive by design, unverified |
| 16b | Production rollout of new migrations | Migrations verified on scratch PG only; owner applies via documented sequence |
| 16c | Backup cron firing on schedule | Timer enabled 2026-10-12; first manual runs verified, unattended firing not yet observed |
| — | Concurrent-refund/payroll races under load | Sequential guards tested; true multi-process races need load testing |

## Open product decisions (owner)

- Standalone (unlinked) goodwill refunds: kept allowed; confirm or forbid.
- Payroll basis: gross collected (current) vs net of refunds/reversals/discounts.
- Negative net payroll (advances/penalties): currently rejected above gross.
- Online payments carry no class attribution: percentage payroll excludes them
  until intake captures enrollment context.
- Phone-ownership proof for public registration: no SMS infra; process decision needed.
- Forged `Status=NOK` callbacks can fail others' PENDING payments: low impact
  (re-initiation), no provider signature exists to gate on.
