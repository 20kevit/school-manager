# Manual Browser Acceptance Procedure

Browser automation is unavailable in this environment (Playwright installs,
but the Chromium download stalls and cannot complete reliably), so the
following flows require a human with a real browser against a **local**
application + disposable database. Never run acceptance against production.

## Setup (disposable)

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.example .env   # local SQLite by default
.venv/bin/flask --app wsgi db upgrade
FLASK_ENV=development .venv/bin/flask --app wsgi seed-demo
.venv/bin/python run.py   # http://127.0.0.1:5000
```

Log in with a seeded account (`admin` / `admin123` — local only).

## Viewports (minimum)

- Desktop 1440×900 (Chrome/Firefox)
- Tablet 820×1180
- Mobile 390×844 (Chrome device emulation is acceptable; note it)

## Flows (each: success path + one invalid input + permission-denied check)

1. **Login/logout/navigation** — wrong password shows Persian error; logout
   is a POST button; sidebar matches role (admin/teacher/student/parent).
2. **Enrollment** — public apply form validates national ID/phone/Jalali
   birth date; admin approves → account activates; forced password rotation
   screen appears on first login with the bootstrap password.
3. **Classes/attendance** — teacher records attendance; student sees own
   records; cross-class URLs return 403 with the Persian error page (not a
   traceback).
4. **Assessments/transcript** — teacher grades; student sees own transcript;
   parent sees linked child only.
5. **Finance** — admin creates charge/payment/refund (refund requires the
   linked payment id); goodwill credit requires a reason; student statement
   and receipt render; dashboard shows billed vs collected figures.
6. **Payroll** — finalize a period; void it; re-finalize with corrected
   deductions; mark paid; double-finalize is rejected with a clear message.
7. **Notifications/files** — upload with entity attach; download matrix;
   event deduplication (run `flask run-jobs` twice → single reminders).
8. **States** — empty lists, 404/403/500 pages render the Persian error
   templates (no raw tracebacks, no `errors/404.html` literal text).
9. **RTL/i18n** — `<html lang="fa" dir="rtl">`; Jalali dates correct around
   month boundaries (test 1403/12/29–1404/01/01); Toman formatting with
   thousands separators; no console errors; no failed `/static/*` requests
   (check DevTools Network + Console and record results).

## Recording results

For each flow record: browser + viewport, pass/fail, screenshot on failure,
console errors (exact text). Update `docs/ACCEPTANCE.md` row 15 when done.
