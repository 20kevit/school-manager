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
| 16c | Backup cron firing on schedule | Timer enabled 2026-10-12; unattended firing observed 2026-10-13 (dump verified) |
| — | Concurrent-refund/payroll/callback races | Proven on PostgreSQL with threaded tests (see `tests/test_pg_concurrency.py`); load testing still pending |

## Decided policies (binding unless explicitly revised)

- Ordinary refunds must link to a real eligible payment (`record_refund`
  requires `related_transaction_id`); goodwill without a payment uses the
  explicit, reasoned, auditable `record_goodwill_credit()` path.
- Payroll revenue basis is **net collected revenue** (ACTIVE payments minus
  linked ACTIVE refunds/reversals per class); discounts excluded; unattributed
  (`class_id` NULL) payments reported on the summary, excluded from classes.
- Negative salary payments are never created: per-class revenue share floors
  at zero with an explicit note; deductions must stay within [0, gross].
  Advances/debts have no workflow and are rejected.
- Online payments without class attribution stay visible in financial
  reporting but excluded from class payroll until intake captures context.
- Phone numbers are **unverified contact data**: possession of a number or a
  submitted form is never proof of ownership. SMS delivery honestly reports
  unavailability; no OTP/verification flow exists. Phone numbers must not
  gate authentication or authorization decisions.
- Failure callbacks are untrusted input: only provider verification mutates
  payment state (see `process_payment_callback` security model).
