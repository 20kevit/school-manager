# Architecture

## Overview

Academy Management System uses a **modular monolith** architecture. The codebase is organized into four layers with strictly enforced dependency direction.

## Layers

```
Interface (routes, templates, API endpoints)
    |
    v
Application (use cases, orchestration, DTOs)
    |
    v
Domain (entities, value objects, domain services, repository interfaces)

Infrastructure (database, external services, email, payment gateways)
    |
    v
Domain / Application contracts (repository interfaces, service interfaces)
```

### Domain Layer

- Contains business entities and rules.
- Framework-agnostic: no Flask, no SQLAlchemy imports.
- Repository interfaces are defined here; implementations live in Infrastructure.

### Application Layer

- Orchestrates use cases.
- Calls domain services and infrastructure.
- Never imports from Interface.

### Infrastructure Layer

- Implements repository interfaces from Domain.
- Contains database models (SQLAlchemy), external service integrations, email, SMS, payment gateways.
- Implements ports defined by Application/Domain.

### Interface Layer

- Flask blueprints, routes, templates, API views.
- Thin controllers: parse input, call Application layer, return response.
- No business logic here.

## Application Factory

`app/__init__.py` exposes `create_app(config_name)` which:

1. Loads configuration.
2. Initializes extensions (SQLAlchemy, Migrate, LoginManager).
3. Registers blueprints.
4. Registers error handlers.

## Configuration

Separate configs per environment (development, testing, production) in `config/__init__.py`. Secrets come from environment variables via `.env`.

## Database

- PostgreSQL in production, SQLite for development/testing.
- SQLAlchemy ORM for models.
- Flask-Migrate (Alembic) for schema migrations.
- Migration workflow: Model change -> Migration -> Test -> Commit.

## Authentication & Authorization

- Flask-Login for session management.
- Werkzeug for password hashing.
- Role-based access control with `role_required` decorator.
- Initial roles: ADMIN, TEACHER, STUDENT, PARENT.
- User model supports multiple roles per user.

## Frontend

- Jinja2 templates with a base layout.
- Vanilla CSS/JS, mobile-first responsive design.
- RTL-ready: Persian language support with `dir="rtl"`.

## API Strategy

- REST/JSON API at `/api/v1/`.
- Separate blueprint (`api_bp`) for API routes.
- Same backend serves web and future mobile clients.

## Adding New Modules

1. Create domain entities in `app/domain/<module>/`.
2. Create repository interfaces in domain.
3. Implement repositories in `app/infrastructure/`.
4. Create application services in `app/application/<module>/`.
5. Create interface (blueprint) in `app/interface/web/` or `app/interface/api/`.
6. Register blueprint in `app/__init__.py`.

## Module Overview

| Module | Domain | Application | Interface | Blueprint |
|--------|--------|-------------|-----------|-----------|
| Auth | user, role, profiles | auth/services | web/auth | auth_bp |
| Academy | course, class_, session | academy/ | web/academy | academy_bp |
| Enrollment | enrollment | enrollment/ | web/enrollment | enrollment_bp |
| Attendance | attendance | attendance/ | web/attendance | attendance_bp |
| Activity | activity, submission | activity/ | web/activity | activity_bp |
| Finance | finance | finance/ | web/finance | finance_bp |
| Assessment | assessment, result | assessment/ | web/assessment | assessment_bp |

## Academy Structure (P2)

The academy structure follows a hierarchical model:

```
Course (reusable template)
  └── Syllabus (ordered content items)
  └── Class (running instance)
        ├── Weekly Schedule (recurring time slots)
        ├── Sessions (generated from schedule)
        └── Session Content Overrides (class-level customization)
```

### Key Design Decisions

- **Course vs Class**: A Course is a reusable educational template. A Class is an actual running instance created from a Course.
- **Capacity at Class level**: Different classes of the same Course can have different capacities.
- **Persisted Sessions**: Sessions are real database records, not dynamically calculated on each request.
- **Schedule Exceptions**: Individual sessions can have custom dates without modifying the recurring schedule.
- **Session Shifting**: Cancelling and shifting preserves session numbering and total planned session count.
- **Content Hierarchy**: Course syllabus → Class-specific overrides → Individual session overrides.

## Enrollment (P3)

The enrollment system manages the relationship between Students and Classes.

```
Student
   ↓
Enrollment
   ↓
Class
```

### Enrollment Lifecycle

```
PENDING → APPROVED
PENDING → REJECTED
PENDING → CANCELLED
APPROVED → CANCELLED
```

### Key Design Decisions

- **Student vs Admin enrollment**: Students can request enrollment (PENDING), Admins can directly enroll students (may be auto-approved).
- **Duplicate prevention**: Only one active enrollment (PENDING or APPROVED) per student per class is allowed.
- **Capacity enforcement**: Capacity is checked at approval time. A class at full capacity cannot have new APPROVED enrollments.
- **Historical records**: Rejected and cancelled enrollments are preserved for historical tracking.
- **Basic eligibility**: At this phase, only basic checks are implemented (student exists, class exists, class is accepting enrollments).

## Attendance (P4)

The attendance system records student presence for individual class sessions.

```
Student
   ↓
Enrollment
   ↓
Class
   ↓
Session
   ↓
Attendance
```

### Attendance Status

- **PRESENT** — student attended
- **ABSENT** — student did not attend
- **LATE** — student arrived late
- **EXCUSED** — absence excused (medical, etc.)

### Key Design Decisions

- **Enrollment-based linking**: Attendance is linked via Enrollment (not directly to Student) to enforce class membership and eligibility.
- **One per session**: Unique constraint on (enrollment_id, session_id) prevents duplicate attendance per student per session.
- **Update not create**: Updating existing attendance modifies the record in-place rather than creating duplicates.
- **Approved enrollment required**: Attendance can only be recorded for APPROVED enrollments (not PENDING or CANCELLED).
- **Historical preservation**: Cancelling an enrollment does not delete existing attendance records.
- **Bulk recording**: Teachers can record attendance for an entire session in a single operation.
- **Server-side authorization**: Teachers can only manage attendance for classes they are assigned to.

## Learning Activities (P5)

The activity system manages homework, projects, quizzes, and other learning activities with student submissions and teacher grading.

```
Course (default activities)
   ↓
Class (class-level activities, copied from Course)
   ↓
Session (session-level activities)
   ↓
Activity
   ↓
Student Submission (versioned)
   ↓
Teacher Review / Grade / Feedback
```

### Activity Scope

Activities support three levels:
- **Course-level**: Default activities that serve as templates
- **Class-level**: Class-specific activities (may be copied from Course defaults)
- **Session-level**: Activities tied to a specific session

Activities may also exist independently (e.g., Final Project) without a Session.

### Submission Versioning

Each submission attempt creates a new historical record (version). Previous submissions are never overwritten. The latest submission is identified by the highest version number.

### Grading Workflow

```
SUBMITTED → GRADED (teacher scores)
SUBMITTED → RETURNED (teacher returns for correction)
RETURNED → RESUBMITTED (student resubmits)
RESUBMITTED → GRADED
```

### Late Submission

Submissions after the deadline are accepted but marked as LATE. No automatic penalty is applied.

### Key Design Decisions

- **Persisted copying**: Course default activities are copied to Class (new DB records), not runtime-inherited.
- **Class isolation**: Class customization does not modify Course defaults; Course changes do not affect existing Classes.
- **Versioned history**: Each submission creates a new record, preserving full submission history.
- **Soft-disable**: Deactivating an activity preserves all historical submissions.
- **File validation**: Server-side validation of file type, size, and MIME type (5 MB max, specific extensions only).
- **Flexible activity types**: The Activity model uses a type field (initially HOMEWORK) designed to support future types (PROJECT, PRACTICE, QUIZ, EXAM) without schema changes.

## Finance (P6)

The finance system manages student accounts, tuition charges, payments, discounts, refunds, and financial history.

```
Student
   ↓
FinancialTransaction (ledger)
   ↑
Class.tuition (snapshot at enrollment)
```

### Transaction Types

- **CHARGE** — tuition, fees, manual charges (negative signed amount)
- **PAYMENT** — student payments (positive signed amount)
- **DISCOUNT** — discounts applied (positive signed amount)
- **REFUND** — refunds issued (negative signed amount)
- **REVERSAL** — reverses a transaction (opposite sign of original)
- **ADJUSTMENT** — manual corrections (signed amount stored directly)

### Balance Calculation

Balance is derived from transactions, not a mutable field:

```
balance = sum(signed_amounts) for all ACTIVE transactions
```

Sign convention: PAYMENT/DISCOUNT are positive (credit); CHARGE/REFUND are negative (debit); REVERSAL/ADJUSTMENT are signed.

### Correction vs Reversal

- **Correction**: marks original as CORRECTED (excluded from balance), creates new corrected entry
- **Reversal**: keeps original ACTIVE (preserved for history), creates REVERSAL entry with opposite sign

### Enrollment Integration

- Approval → automatic tuition charge (idempotent)
- Cancellation → REVERSAL entry (original preserved)
- Tuition snapshot preserved from Class.tuition at enrollment time

### Access Control

- Admin: full access to all finance features
- Parent: limited to linked children only
- Student: only 18+ years old can access finance; blocked otherwise

## Payment Integration (Future)

```
Application
    |
    v
Payment Service
    |
    v
Gateway Interface (abstract)
    +-- ZarinPal
    +-- Other Iranian Gateway
    +-- Future Gateway
```

The domain defines the payment port; infrastructure implements each gateway.

## Exams, Assessments & Grades (P7)

The assessment system manages academic evaluations, grading, and student results.

```
Class
  ↓
Assessment (types: FINAL_EXAM, MIDTERM, QUIZ, PROJECT, PRACTICAL, ORAL, OTHER)
  ↓
AssessmentResult (linked via Enrollment)
  ↓
GradeHistory (audit trail for corrections)
```

### Assessment Lifecycle

```
DRAFT → SCHEDULED → OPEN → CLOSED → GRADED
DRAFT → CANCELLED
SCHEDULED → CANCELLED
OPEN → CANCELLED
```

### Grading System

- Numeric 0–100 scale (configurable max_score per assessment)
- Percentage calculated as `score / max_score * 100`
- Pass/Fail determined by assessment's passing_score threshold
- Absent/Excused states for non-numeric results
- Grade history preserved for all corrections

### Key Design Decisions

- **Assessment belongs to Class**: Different classes may have different assessments
- **Enrollment-based eligibility**: Only APPROVED enrollments are eligible for assessment results
- **Configurable max score**: Each assessment defines its own maximum score
- **Grade corrections**: History is preserved; original scores are never silently overwritten
- **Historical preservation**: Results survive enrollment cancellation
- **Bulk grading**: Teachers can grade entire assessments in a single operation
- **Authorization**: Teachers only access their assigned classes; students see only their own results

## Notification Integration (Future)

External communication providers (SMS, Telegram, Bale, Email) belong in `app/infrastructure/`. The domain defines notification interfaces; infrastructure implements them per provider.
