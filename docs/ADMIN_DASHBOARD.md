# Admin Dashboard

The administrator landing page (`GET /portal/admin`, `ADMIN` role only) answers:
current academy state, what needs attention today, class/enrollment/attendance
status, financial pulse, and the next action (one click on the card).

Renderer: `templates/portal/admin.html` with SVG chart macros in
`templates/macros/charts.html`. Aggregator:
`app.application.portal.portal_service.get_admin_dashboard()`. No business
logic lives in templates; finance figures always come from `finance_service`.

## Page sections

1. Compact header: title, live-operations subtitle, Jalali date, active
   academic year/semester (when configured), safe GET refresh link.
2. Quick actions (7 verified workflows): add student/teacher
   (`admin.user_create`), create course/class, enroll student, attendance,
   record payment.
3. Executive KPI summary (8 whole-card `<a>` links, no footer link text):
   active students, active teachers, running classes, courses, approved
   enrollments, pending requests, current-month net collections (with a
   signed comparison against the previous month, omitted when the previous
   month has no data), outstanding debt. Every card links to the exact
   filtered population (see link map below).
4. Needs-attention list: pending enrollments, debtors, unrecorded today
   sessions, OPEN assessments (in progress), CLOSED assessments (awaiting
   grading, each with its own `?status=` link), near-full classes (≥90%
   fill), onboarding hint for an empty academy. Items disappear when
   resolved; a calm empty state otherwise.
5. Analytical charts (server-rendered SVG, no JS dependency, RTL
   right-to-left time axis, `<details>` data tables as alternatives):
   - Monthly collections (12 months): net bars (principal, canonical
     definition) + gross line (secondary), Jalali month labels, Toman units.
   - Monthly enrollments (12 months): requests vs approvals grouped bars.
     Both are operational monthly counts, not a cohort conversion rate;
     approval month uses `approved_at` only (never inferred).
   - 7-day attendance completion: percent of fully-recorded sessions per
     day; days without recordable sessions render as gaps, never 0%.
6. Today's classes table with per-session attendance status and a capacity
   meter (approved/capacity) per row.
7. Pending enrollment requests (5 most recent) with review links.
8. Financial snapshot: month net/gross, billed tuition vs cumulative net
   collected, top-5 debtors with statement links.
9. Links to specialist modules (reporting, audit log). No activity feed: the
   audit log covers only finance/grade events, so a reconstructed feed would
   be misleading; the dashboard links to `/admin/audit-logs` instead.

## Metric definitions

| KPI | Definition | Source |
|---|---|---|
| Active students | Users with `STUDENT` role and `is_active_user=True` | `user_roles` join |
| New students | Active students with `created_at` within the last 30 days | same + `created_at >= now-30d` |
| Active teachers | Users with `TEACHER` role and `is_active_user=True` | `user_roles` join |
| Running classes | Classes with status `ACTIVE` (matches reporting-service convention) | `academy_classes.status` |
| Planned / upcoming | `PLANNED` count; operational classes with `start_date > today` | same + `start_date` |
| Distinct courses | Row count of the `courses` table (never class count) | `courses` |
| Approved enrollments | Enrollments with status `APPROVED` (one student may have many) | `enrollments.status` |
| Pending enrollments | Enrollments with status `PENDING` | same |
| Approved students | `COUNT(DISTINCT student_user_id)` over approved enrollments | same |
| Assessments | Total non-cancelled; OPEN and CLOSED tracked separately | `assessments.status` |
| Month collections (net) | Canonical net (payments − refunds + signed reversals) for the current Gregorian month | `finance_service.get_monthly_revenue()` |
| Month collections (gross) | Sum of `ACTIVE` `PAYMENT` rows in the current Gregorian month | `finance_service.get_dashboard_summary().month_payments` |
| Billed vs collected | `ACTIVE` `CHARGE/TUITION` vs cumulative canonical net | finance service |
| Outstanding debt / debtors | Sum of absolute negative student balances / count of debtors; only `ACTIVE` rows feed balances | finance service |
| Today's attendance | Sessions dated today with status != `CANCELLED`; recorded only when rows exist for **all** approved enrollments; sessions with no approved enrollments are neutral (never flagged, excluded from the rate) | `sessions` + `attendances` |
| Weekly attendance | Same completeness rule applied per day over the last 7 days | same, grouped queries |
| Capacity watch | Operational classes with approved/capacity ≥ 90% | grouped query |
| Trends (12 months) | Gross/net per Gregorian month (labels show Jalali month); refunds/reversals attributed by creation month, identical to per-month `get_revenue_report()` | `finance_service.get_monthly_revenue()` (one conditional-aggregation query) |

Month boundaries are Gregorian calendar months, consistent with
`finance_service.get_dashboard_summary()`. UI dates render in Jalali via the
`jalali` / `jalali_datetime` filters; the database always stores Gregorian.

## Link map (every KPI destination implements its filter)

| Card / item | Destination |
|---|---|
| Students | `admin.user_list?role=STUDENT` (active status shown per row) |
| Teachers | `admin.user_list?role=TEACHER` |
| Running classes | `academy.class_list?status=ACTIVE` (status dropdown added) |
| Courses | `academy.course_list` |
| Approved enrollments | `enrollment.admin_enrollment_list?status=APPROVED` |
| Pending requests | `enrollment.admin_pending_list` |
| Month collections | `finance.admin_dashboard` |
| Debt | `finance.admin_debt_report` |
| OPEN / CLOSED assessments | `assessment.admin_assessment_list?status=OPEN (CLOSED)` |
| Capacity item | `academy.class_detail` for the fullest class |
| Today rows | `attendance.admin_session_attendance` per session |

## Resilience

Core KPI queries propagate failures (loud 500, never silent zeros). Optional
sections (monthly revenue, enrollment trend, today, week, debtors, capacity)
go through `_optional()`, which logs and returns `None`; the template renders
an explicit error state. The month KPI falls back to direct canonical calls
when the trend query fails.

## Performance (PostgreSQL 16, disposable scratch DB, synthetic data:
40 students, 5 classes with sessions, 20 debtors/payments)

- Before (previous dashboard): service ~349 ms / 76 queries, page ~377 ms /
  77 queries.
- After: service ~433 ms / 46 queries, page ~621 ms / 47 queries.
- Query volume fell ~40%: monthly trends went from 12+12 aggregates to 2
  grouped queries; today/week sections use grouped eligible/recorded counts
  (constant queries regardless of session count); debtor names load in one
  query; teacher profiles eager-load in one query; dead `recent_classes`
  query removed.
- Wall-clock times on the shared VPS are noisy (both runs on fresh,
  un-analyzed databases under host load); the structural win is the query
  count, and full-page time stays comfortably under one second.

## Running dashboard tests and browser validation

```bash
.venv/bin/python -m pytest tests/test_admin_dashboard.py -q
.venv/bin/python -m pytest tests/ -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Browser validation (never production; local test server + seeded SQLite):
Playwright with system Chrome at 1440/768/390/320, login flow, screenshot
review, console/network error check, KPI-card click-through, keyboard
Tab/Enter activation, focus-ring check, empty-academy render. Note: with
ruff 0.17, never run bare `ruff format` on this repo — its formatter
corrupts multi-exception `except` tuples (use `--check` plus hand edits and
`# fmt: skip` guards, following the existing pattern in `app/__init__.py`).

## Known limitations / deferred

- Server runs on UTC while the academy follows Asia/Tehran: "today" and
  month boundaries use the server-local date project-wide (same convention
  as finance/enrollment services). Metrics are exact except inside the
  00:00–03:30 Tehran window around midnight/month-turn.
- No configurable widgets, no global search, no AI insights (per scope).
- No payroll figures on the dashboard (kept separate from student fees).
- Recent-activity feed omitted: the audit log covers only finance/grade
  events, so a reconstructed feed would be misleading; link to the audit
  log is provided instead.
