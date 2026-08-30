# ADR-004: Assessment Architecture

## Status

Accepted

## Context

The Academy Management System needs an academic assessment system to support exams, quizzes, projects, and other evaluations with grading, pass/fail determination, and grade history.

Key requirements:
- Support multiple assessment types (FINAL_EXAM, MIDTERM, QUIZ, PROJECT, etc.)
- Class-level assessments (not course-level)
- Configurable max score and passing score per assessment
- Grade correction history
- Enrollment-based eligibility
- Teacher, Student, Parent, and Admin access

## Decision

### Assessment belongs to Class (not Course)

Assessments are linked directly to AcademyClass, not to Course. This allows:
- Different classes to have different exams
- Different dates, max scores, and passing scores per class
- Class-specific grading workflows

Course-level assessment templates may be added in the future by copying assessments from Course to Class (similar to how activities are copied).

### Grade corrections create history entries

When a grade is corrected, the system creates a GradeHistory entry preserving:
- Previous score and pass/fail status
- New score and pass/fail status
- Who corrected it and when
- Reason for correction

The original AssessmentResult is updated in-place (not duplicated) to maintain a single source of truth per student per assessment.

### Results linked via Enrollment

Following the existing Attendance pattern, AssessmentResult is linked via Enrollment (not directly to Student + Class). This:
- Enforces class membership eligibility
- Preserves historical results when enrollment is cancelled
- Maintains consistency with the rest of the domain

### Configurable max score per assessment

Each assessment stores its own max_score and passing_score. The system calculates:
- `percentage = score / max_score * 100`
- `pass_fail = PASS if score >= passing_score else FAIL`

This avoids global assumptions about grading scales and supports future weighted grading.

### Assessment lifecycle statuses

The assessment uses a simple state machine:
```
DRAFT → SCHEDULED → OPEN → CLOSED → GRADED
Any non-CANCELLED state → CANCELLED
```

This is intentionally simple. A more complex state machine may be needed for multi-stage assessments in the future.

### Assessment types are extensible

The type field uses a string enum with 7 initial values. New types can be added without schema changes. The domain model does not constrain future assessment categories.

## Consequences

### Positive
- Class-level assessment ownership provides natural isolation
- Grade history preserves audit trail without complex versioning
- Enrollment-based eligibility reuses existing domain concepts
- Configurable scores support diverse assessment types
- Simple lifecycle is sufficient for initial use

### Negative
- Course-level assessment templates require explicit copying (not automatic inheritance)
- Grade history is append-only (no rollback mechanism)
- Weighted grading is not yet implemented (architecturally supported)
- Multi-attempt assessments are not yet supported

### Risks
- AssessmentResult unique constraint on (assessment_id, enrollment_id) means one result per student per assessment. Future multi-attempt support will require schema changes.
