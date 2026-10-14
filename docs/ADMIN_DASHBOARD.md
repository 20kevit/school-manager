# Admin Dashboard

The administrator landing page (`GET /portal/admin`, `ADMIN` role only) answers:
current academy state, what needs attention today, class/enrollment/attendance
status, financial pulse, and the next action (one click to the record).

Renderer: `templates/portal/admin.html`. Aggregator:
`app.application.portal.portal_service.get_admin_dashboard()`. No business logic
lives in the template; finance figures always come from `finance_service`.

## Metric definitions

| KPI | Definition | Source |
|---|---|---|
| Active students | Users with `STUDENT` role and `is_active_user=True` | `user_roles` join |
| New students | Active students with `created_at` within the last 30 days | same + `created_at >= now-30d` |
| Active teachers | Users with `TEACHER` role and `is_active_user=True` | `user_roles` join |
| Active classes | Classes with status `PLANNED` or `ACTIVE` (both accept enrollments) | `academy_classes.status` |
| Upcoming classes | Active classes with `start_date > today` | same + `start_date` |
| Distinct courses | Row count of the `courses` table (never class count) | `courses` |
| Approved enrollments | Enrollments with status `APPROVED` (one student may have many) | `enrollments.status` |
| Pending enrollments | Enrollments with status `PENDING` | same |
| Approved students | `COUNT(DISTINCT student_user_id)` over approved enrollments | same |
| Assessments (total) | Assessments with status != `CANCELLED` | `assessments.status` |
| Assessments needing follow-up | Status `OPEN` (in progress) or `CLOSED` (awaiting grading) | same |
| Month collections (gross) | Sum of `ACTIVE` `PAYMENT` rows created in the current Gregorian month | `finance_service.get_dashboard_summary().month_payments` |
| Month collections (net) | Canonical `get_revenue_report()` net (payments − refunds + signed reversals) for the current vs previous Gregorian month | `finance_service.get_revenue_report()` |
| Outstanding debt / debtors | Sum of absolute negative student balances / count of debtors; only `ACTIVE` rows feed balances | `finance_service.get_dashboard_summary()` |
| Today's attendance | Sessions dated today with status != `CANCELLED`; a session is recorded only when attendance rows exist for **all** approved enrollments (absence of rows is never presence) | `sessions` + `attendances` |
| Trends (6 months) | Gross `PAYMENT` sums and `APPROVED` counts per Gregorian month (labels show Jalali month) | inline aggregates, same transaction semantics |

Month boundaries are Gregorian calendar months, consistent with
`finance_service.get_dashboard_summary()`. UI dates render in Jalali via the
`jalali` / `jalali_datetime` filters; the database always stores Gregorian.

## Sections

1. Header: greeting, Jalali date, active academic year/semester (when
   configured), safe GET refresh link.
2. Quick actions (7 verified workflows): add student/teacher (`admin.user_create`),
   create course/class, enroll student, attendance, record payment.
3. KPI cards (8, all clickable to the matching filtered list).
4. Requires-attention list: pending enrollments, debtors, unrecorded today
   sessions, OPEN/CLOSED assessments, onboarding hint for an empty academy.
   Items disappear when resolved; a calm empty state otherwise.
5. Today's classes table with per-session attendance-recording status.
6. Pending enrollment requests (5 most recent) with review links.
7. Financial pulse: gross vs net month collections with previous-month
   comparison (omitted when the previous month has no data), billed tuition vs
   cumulative net collected, top-5 debtors with statement links.
8. Two CSS-only bar charts (collections, admissions) with `<details>` data
   tables as accessible alternatives. No charting dependency.
9. Links to specialist modules (reporting, audit log). No activity feed: the
   audit log covers only finance/grade events, so a reconstructed feed would
   be misleading; the dashboard links to `/admin/audit-logs` instead.

## Resilience

Core KPI queries propagate failures (loud 500, never silent zeros). Optional
sections (trends, today's schedule, debtor ranking) go through `_optional()`,
which logs and returns `None`; the template renders an explicit error state.

## Performance (measured, SQLite testing config, seeded demo: 12 students,
3 classes with sessions, 6 debtors/payments)

- `get_admin_dashboard()`: ~116 ms, 66 queries (bounded: 20 sessions, 5+5+5
  rows, 12 trend buckets, 2 revenue reports).
- Full page GET: ~530 ms, 67 queries, 200 OK.
- No N+1: recent pendings use `joinedload`; per-session counts are aggregate
  queries, not entity loads.

## Known limitations / deferred

- Server runs on UTC while the academy follows Asia/Tehran: "today" and
  month boundaries use the server-local date project-wide (same convention
  as finance/enrollment services). Metrics are exact except inside the
  00:00–03:30 Tehran window around midnight/month-turn.
- Class list has no status filter, so the active-classes card links to the
  unfiltered (but correct-module) class list; enrollment list supports all
  status filters and student/teacher cards link to role-filtered user lists.
- Favicon 404 (`/favicon.ico` has never existed) — pre-existing, untouched.
- No configurable widgets, no global search, no AI insights (per scope).
- Attendance trend chart omitted: no trustworthy historical denominator is
  established; today's completion is shown instead.
- Recent-activity feed omitted (see §9); link to audit log provided.
