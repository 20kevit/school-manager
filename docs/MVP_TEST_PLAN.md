# MVP Test Plan — Academy Management System

Browser-based manual testing plan for validating the application end-to-end.

---

## Setup Instructions

### Initialize the Database

```powershell
.venv\Scripts\activate
$env:FLASK_APP="run.py"
flask db upgrade
```

This creates all tables in `school_manager_dev.db` (SQLite).

### Seed Test Data

```powershell
flask seed
```

This creates the 4 standard roles, test users, and a fully populated test environment:

| Role | Login | Password |
|------|-------|----------|
| Admin | `admin` | `admin123` |
| Teacher | `teacher1` | `teacher123` |
| Student | `student1` | `student123` |
| Parent | `parent1` | `parent123` |

The seed script also creates:
- A sample course ("ریاضی کنکور") with 5 syllabus items
- A sample class ("کلاس رضا") assigned to teacher1 with weekly schedule
- 5 class sessions (2 completed, 3 scheduled)
- An approved enrollment for student1
- A sample homework activity ("تمرین فصل اول")
- A midterm assessment ("آزمون میان‌ترم")
- A tuition charge for student1

The command is idempotent — running it twice will not create duplicates. No manual shell data entry is needed.

### Start the Server

```powershell
python run.py
```

Open `http://127.0.0.1:5000` in browser.

---

## Route Map

### Entry Points

| URL | Description | Access |
|-----|-------------|--------|
| `/` | Index page (shows "Academy Management System" text) | Public |
| `/auth/login` | Login page | Public |
| `/auth/logout` | Logout | Authenticated |
| `/auth/change-password` | Change password | Authenticated |
| `/health` | Health check (JSON) | Public |

### Portal Dashboards (after login, auto-redirect)

| URL | Role |
|-----|------|
| `/portal/admin` | ADMIN |
| `/portal/teacher` | TEACHER |
| `/portal/student` | STUDENT |
| `/portal/parent` | PARENT |

### Admin Routes

| URL | Description |
|-----|-------------|
| `/admin/users` | User list with search and role filter |
| `/admin/users/create` | Create new user |
| `/admin/users/<id>/edit` | Edit user profile, reset password, manage parent-student links |
| `/academy/courses` | Course list |
| `/academy/courses/create` | Create course |
| `/academy/classes` | Class list |
| `/academy/classes/create` | Create class |
| `/enrollment/admin/all` | Enrollment list |
| `/enrollment/admin/pending` | Pending enrollments |
| `/enrollment/admin/enroll` | Direct enrollment |
| `/attendance/admin/all` | Attendance list |
| `/activity/admin/all` | Activity list |
| `/activity/admin/create` | Create activity |
| `/assessment/admin/all` | Assessment list |
| `/assessment/admin/create` | Create assessment |
| `/finance/admin/dashboard` | Finance dashboard |
| `/finance/admin/transaction/create` | Create transaction |
| `/finance/admin/reports/debt` | Debt report |
| `/notification/admin` | Notification dashboard |
| `/notification/admin/manual` | Send manual notification |
| `/notification/admin/announcement` | Send announcement |
| `/notification/admin/templates` | Template management |
| `/reporting/admin/overview` | Reports overview |
| `/reporting/admin/operational` | Operational report |
| `/reporting/admin/attendance` | Attendance report |
| `/reporting/admin/finance` | Finance report |
| `/files/admin` | File management |
| `/files/admin/orphans` | Orphan files |

### Teacher Routes

| URL | Description |
|-----|-------------|
| `/attendance/teacher/my-classes` | My classes (attendance) |
| `/activity/teacher/my-classes` | My classes (activities) |
| `/assessment/teacher/my-classes` | My classes (assessments) |
| `/reporting/teacher/overview` | Teacher reports |

### Student Routes

| URL | Description |
|-----|-------------|
| `/enrollment/student/classes` | Available classes |
| `/enrollment/student/my-enrollments` | My enrollments |
| `/attendance/student/my-attendance` | My attendance |
| `/activity/student/my-classes` | My classes (activities) |
| `/assessment/student/my-assessments` | My assessments |
| `/finance/student/my-finance` | My finance |
| `/notification/my` | My notifications |
| `/reporting/student/overview` | Student reports |

### Parent Routes

| URL | Description |
|-----|-------------|
| `/assessment/parent/overview` | Children results |
| `/finance/parent/overview` | Children finance |
| `/reporting/parent/child/<id>` | Child report |

---

## Test Scenarios

### Scenario A — Authentication & Admin Dashboard

**ID:** A-01
**Priority:** P0
**Preconditions:** Server running, database seeded

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `http://127.0.0.1:5000` | Page loads with sidebar, title "آکادمی" |
| 2 | Navigate to `http://127.0.0.1:5000/auth/login` | Login form with Persian labels |
| 3 | Login as `admin` / `admin123` | Redirects to `/portal/admin` |
| 4 | Verify admin dashboard | Shows stats cards, pending enrollments, financial summary |
| 5 | Verify sidebar links | All admin links visible: دوره‌ها, کلاس‌ها, ثبت‌نام, حضور و غیاب, تکالیف, ارزیابی, مالی, اعلان‌ها, گزارش‌ها, فایل‌ها |
| 6 | Click "خروج" | Redirects to login page |
| 7 | Try accessing `/portal/admin` without login | Redirects to `/auth/login` |
| 8 | Login as `teacher1` / `teacher123` | Redirects to `/portal/teacher` |
| 9 | Verify teacher sidebar | Shows: کلاس‌های من, تکالیف, ارزیابی, گزارش‌ها |
| 10 | Login as `student1` / `student123` | Redirects to `/portal/student` |
| 11 | Verify student sidebar | Shows: کلاس‌ها, ثبت‌نام‌های من, حضور و غیاب, تکالیف, نتایج, وضعیت مالی, اعلان‌ها, گزارش‌ها |
| 12 | Login as `parent1` / `parent123` | Redirects to `/portal/parent` |
| 13 | Verify parent sidebar | Shows: نتایج فرزندان, وضعیت مالی فرزندان |

---

### Scenario B — Course & Class Management

**ID:** B-01
**Priority:** P0
**Preconditions:** Logged in as admin

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/academy/courses` | Empty course list or existing courses |
| 2 | Click "ایجاد دوره" (create course) | Course create form loads |
| 3 | Fill: title="ریاضی پایه", description="دوره ریاضی", num_sessions=20, min_age=12, max_age=15 | Form accepts input |
| 4 | Submit form | Redirects to course list, new course appears |
| 5 | Click on course name | Course detail page with syllabus section |
| 6 | Add syllabus item: title="فصل ۱", content="معرفی اعداد" | Syllabus item appears in list |
| 7 | Navigate to `/academy/classes` | Class list loads |
| 8 | Click "ایجاد کلاس" | Class create form loads |
| 9 | Fill: title="ریاضی پایه-گروه الف", course=ریاضی پایه, capacity=20, start_date, end_date | Form accepts input |
| 10 | Add weekly schedule: Saturday 10:00-12:00 | Schedule entry appears |
| 11 | Submit form | Redirects to class list, new class appears |
| 12 | Click on class name | Class detail page with schedule and session info |
| 13 | Verify sessions were generated | Session list shows 20 sessions |

---

### Scenario C — Enrollment

**ID:** C-01
**Priority:** P0
**Preconditions:** Course and class exist, teacher assigned

#### Path 1: Admin Direct Enrollment

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as admin, go to `/enrollment/admin/enroll` | Enrollment form loads |
| 2 | Select student and class | Form accepts selection |
| 3 | Submit | Redirects to enrollment list, status=APPROVED |
| 4 | Verify class capacity updated | Enrolled count increases |

#### Path 2: Student Request + Admin Approval

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as student, go to `/enrollment/student/classes` | Available classes list |
| 2 | Click on a class | Class detail with "درخواست ثبت‌نام" button |
| 3 | Click enrollment request | Redirects to my-enrollments, status=PENDING |
| 4 | Login as admin, go to `/enrollment/admin/pending` | Pending request appears |
| 5 | Click approve | Redirects to enrollment detail, status=APPROVED |

#### Capacity & Duplicate Tests

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Enroll student in class at full capacity | Error: class is full |
| 2 | Enroll student already enrolled in same class | Error: duplicate enrollment |
| 3 | Cancel an approved enrollment | Status changes to CANCELLED |
| 4 | Reject a pending enrollment | Status changes to REJECTED |

---

### Scenario D — Attendance

**ID:** D-01
**Priority:** P0
**Preconditions:** Teacher assigned to class, students enrolled, sessions generated

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as teacher, go to `/attendance/teacher/my-classes` | Assigned classes list |
| 2 | Click on class | Class sessions list |
| 3 | Click on a session (today or past) | Attendance form with enrolled students |
| 4 | Mark student PRESENT, another ABSENT, another LATE | Status selects work |
| 5 | Submit attendance | Redirects to session list, attendance recorded |
| 6 | Re-open the same session | Previous attendance values restored |
| 7 | Change ABSENT to PRESENT | Update succeeds |
| 8 | Login as student, go to `/attendance/student/my-attendance` | Attendance history shows correct records |
| 9 | Try accessing another class's attendance as teacher | 403 Forbidden |

---

### Scenario E — Learning Activities (Homework)

**ID:** E-01
**Priority:** P1
**Preconditions:** Class with sessions exists

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as admin/teacher, create activity | Activity form loads |
| 2 | Set: title="تکلیف فصل ۱", type=HOMEWORK, required=true, deadline | Form accepts input |
| 3 | Submit | Activity appears in class activity list |
| 4 | Login as student, go to `/activity/student/my-classes` | Classes with activities |
| 5 | Open activity detail | Activity info + submission form |
| 6 | Submit text content | Submission recorded, status=SUBMITTED |
| 7 | Re-submit with different text | New version created, history shows both |
| 8 | Login as teacher, open submission | Submission detail loads |
| 9 | Grade: score=85, feedback="خوب بود" | Grade recorded |
| 10 | Return for resubmission | Status changes to RETURNED |
| 11 | Student re-submits | New version, status back to SUBMITTED |
| 12 | Teacher grades again | New grade recorded, history preserved |

---

### Scenario F — Exams & Grades

**ID:** F-01
**Priority:** P1
**Preconditions:** Class with enrolled students

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as admin, go to `/assessment/admin/create` | Assessment form loads |
| 2 | Fill: title="امتحان میان‌ترم", type=MIDTERM, max_score=100, passing_score=60, class | Form accepts |
| 3 | Submit | Assessment detail page, status=DRAFT |
| 4 | Change status to OPEN | Status updates |
| 5 | Go to grade page, enter scores for each student | Grades accepted |
| 6 | Test bulk grading | All grades saved |
| 7 | Correct a grade (change 70 to 85) | Grade updated, history entry created |
| 8 | Login as student, go to `/assessment/student/my-assessments` | Assessment appears |
| 9 | View result detail | Score, grade, pass/fail shown |
| 10 | Login as parent, go to `/assessment/parent/overview` | Children's results visible |

---

### Scenario G — Finance

**ID:** G-01
**Priority:** P0
**Preconditions:** Student enrolled in a paid class (tuition set)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as admin, go to `/finance/admin/dashboard` | Finance dashboard with summary |
| 2 | Verify automatic tuition charge | Transaction appears for enrollment |
| 3 | Go to `/finance/admin/student/<id>/statement` | Student statement shows CHARGE |
| 4 | Go to `/finance/admin/transaction/create` | Transaction form loads |
| 5 | Create PAYMENT transaction for student | Payment recorded |
| 6 | Verify student statement | Shows CHARGE and PAYMENT, balance updated |
| 7 | Create DISCOUNT transaction | Discount recorded |
| 8 | Verify debt report | Student appears with correct outstanding |
| 9 | Create REVERSAL of a payment | Reversal recorded, balance restored |
| 10 | Create CORRECTION of a transaction | Original marked CORRECTED, new entry created |
| 11 | Login as student, go to `/finance/student/my-finance` | Student sees own finance (if 18+) |
| 12 | Login as parent, go to `/finance/parent/overview` | Parent sees linked children's finance |

---

### Scenario H — Notifications

**ID:** H-01
**Priority:** P2
**Preconditions:** Logged in as admin

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Go to `/notification/admin` | Notification dashboard |
| 2 | Go to `/notification/admin/manual` | Manual notification form |
| 3 | Send notification to a user | Notification created |
| 4 | Go to `/notification/admin/announcement` | Announcement form |
| 5 | Send announcement | Announcement sent to multiple users |
| 6 | Login as recipient, go to `/notification/my` | Notification list with unread items |
| 7 | Click read | Notification marked as read |
| 8 | Go to `/notification/preferences` | Preferences form |
| 9 | Toggle a channel off | Preference saved |

---

### Scenario I — Reports

**ID:** I-01
**Priority:** P2
**Preconditions:** Data exists in system

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as admin, go to `/reporting/admin/overview` | Overview dashboard |
| 2 | Go to `/reporting/admin/operational` | Today's classes, pending items |
| 3 | Go to `/reporting/admin/attendance` | Attendance report with filters |
| 4 | Apply filter (specific class) | Filtered results shown |
| 5 | Export CSV | CSV downloads with correct data |
| 6 | Login as teacher, go to `/reporting/teacher/overview` | Only own classes visible |
| 7 | Login as student, go to `/reporting/student/overview` | Only own data visible |

---

### Scenario J — File Management

**ID:** J-01
**Priority:** P2
**Preconditions:** Logged in

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Upload a file (e.g., homework submission) | File uploaded successfully |
| 2 | Download the file | File downloads correctly |
| 3 | Login as admin, go to `/files/admin` | File list with uploaded file |
| 4 | Click on file detail | File metadata shown |
| 5 | Delete file | File marked deleted |
| 6 | Try uploading disallowed extension | Error message |
| 7 | Try uploading oversized file | Error message |
| 8 | Try accessing another user's private file | 403 Forbidden |

---

### Scenario K — Role Security Smoke Test

**ID:** K-01
**Priority:** P0
**Preconditions:** All users created

| Test | Role | URL Attempted | Expected |
|------|------|---------------|----------|
| K-01-1 | Student | `/academy/courses` | 403 |
| K-01-2 | Student | `/enrollment/admin/all` | 403 |
| K-01-3 | Student | `/attendance/admin/all` | 403 |
| K-01-4 | Student | `/finance/admin/dashboard` | 403 |
| K-01-5 | Teacher | `/finance/admin/dashboard` | 403 |
| K-01-6 | Teacher | `/assessment/admin/all` | 403 |
| K-01-7 | Parent | `/academy/courses` | 403 |
| K-01-8 | Admin | `/attendance/student/my-attendance` | 403 |
| K-01-9 | Unauthenticated | `/portal/admin` | Redirect to login |

---

### Scenario L — Responsive & UX

**ID:** L-01
**Priority:** P2
**Preconditions:** Any logged-in user

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Resize browser to desktop (>1024px) | Sidebar persistent, content fills space |
| 2 | Resize to tablet (768-1024px) | Sidebar hidden, hamburger menu visible |
| 3 | Resize to mobile (<768px) | Sidebar hidden, hamburger works, tables scroll horizontally |
| 4 | Open sidebar on mobile | Sidebar slides in, overlay visible |
| 5 | Click overlay | Sidebar closes |
| 6 | Check flash messages | Auto-dismiss after 5 seconds |
| 7 | Submit empty required form | Validation errors shown in Persian |
| 8 | Check RTL alignment | All text right-aligned, numbers left-aligned |
| 9 | Check long Persian text | No horizontal overflow |
| 10 | Check tables with many columns | Horizontal scroll works |

---

## Test Matrix

| ID | Area | Preconditions | Actions | Expected Result | Priority |
|----|------|---------------|---------|-----------------|----------|
| A-01 | Auth | DB seeded | Login all 4 roles, verify dashboards and sidebar links | Correct role-based redirect and sidebar | P0 |
| B-01 | Academy | Admin logged in | Create course, syllabus, class, schedule, sessions | Full course/class lifecycle works | P0 |
| C-01 | Enrollment | Course+class exist | Admin enroll, student request, approve/reject, capacity, duplicate | Enrollment lifecycle works | P0 |
| D-01 | Attendance | Teacher assigned, students enrolled | Record, update, verify student/parent view | Attendance tracking works | P0 |
| E-01 | Activity | Class with sessions | Create, submit, resubmit, grade, return | Homework workflow works | P1 |
| F-01 | Assessment | Class with students | Create, configure, grade, bulk grade, correct, verify history | Grading workflow works | P1 |
| G-01 | Finance | Student in paid class | Tuition charge, payment, discount, reversal, correction, reports | Financial lifecycle works | P0 |
| H-01 | Notification | Admin logged in | Send manual, announcement, verify read/unread, preferences | Notification system works | P2 |
| I-01 | Reports | Data exists | View reports, filter, export CSV, verify role limits | Reporting works | P2 |
| J-01 | Files | Any user | Upload, download, replace, delete, validation, auth | File management works | P2 |
| K-01 | Security | All users | Cross-role URL access attempts | 403 for unauthorized access | P0 |
| L-01 | Responsive | Any user | Desktop/tablet/mobile, sidebar, RTL, forms, tables | UI works across devices | P2 |

---

## Current Valid Entry URLs

| URL | Description | Access |
|-----|-------------|--------|
| `http://127.0.0.1:5000/` | Index page | Public |
| `http://127.0.0.1:5000/auth/login` | Login | Public |
| `http://127.0.0.1:5000/portal/admin` | Admin dashboard | ADMIN |
| `http://127.0.0.1:5000/portal/teacher` | Teacher dashboard | TEACHER |
| `http://127.0.0.1:5000/portal/student` | Student dashboard | STUDENT |
| `http://127.0.0.1:5000/portal/parent` | Parent dashboard | PARENT |
| `http://127.0.0.1:5000/health` | Health check | Public |

## Test Credentials

| Role | Login | Password |
|------|-------|----------|
| Admin | `admin` | `admin123` |
| Teacher | `teacher1` | `teacher123` |
| Student | `student1` | `student123` |
| Parent | `parent1` | `parent123` |

---

### Scenario M — Calendar & Profile (P14)

**ID:** M-01
**Priority:** P0
**Preconditions:** Server running, database seeded

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as admin, go to `/academy/classes/create` | Class form loads with Jalali date inputs (-placeholder: ۱۴۰۵/۰۷/۰۱) |
| 2 | Fill start_date as `1405/07/01`, submit with valid schedule | Class created successfully, dates stored as Gregorian |
| 3 | Open class detail page | Start/end dates displayed in Jalali format |
| 4 | Open session list for the class | All session dates displayed in Jalali format |
| 5 | Click on a session, click "ویرایش جلسه" | Session edit form loads with Jalali date |
| 6 | Change the session date to `1405/08/01`, submit | Session updated, rescheduled=true, edit history recorded |
| 7 | Open session detail | Edit history shows previous and new dates |
| 8 | Login as student, go to `/auth/profile` | Profile page loads with Jalali birth_date |
| 9 | Edit first_name, last_name, mobile_phone, birth_date | Profile updated successfully |
| 10 | Verify national_id and username are read-only | Cannot modify protected fields |
| 11 | Upload profile photo (JPG) | Photo uploaded, displayed on profile page |
| 12 | Replace profile photo | Old photo marked deleted, new photo displayed |
| 13 | Login as admin, go to `/finance/admin/student/<id>/statement` | Category column shows Persian labels (شهریه, not TUITION) |
| 14 | Check `/finance/admin/transaction/<id>/detail` | Category and payment_method show Persian labels |
| 15 | Login as student, check `/finance/student/my-finance` | Category column shows Persian labels |
| 16 | Navigate to `/` (unauthenticated) | Landing page loads with 6 feature cards, RTL, Persian |
| 17 | Verify landing page on mobile viewport | Responsive layout, single-column features |
| 18 | Login from landing page | Redirects to role-specific dashboard |

---

## Known Limitations

1. **No file upload UI on forms** — File upload only works via dedicated upload endpoints
2. **External notification providers unconfigured** — SMS/Telegram/Bale/Email require credentials in `.env`
3. **No ZarinPal integration** — Finance is cash-only (manual transaction recording)
