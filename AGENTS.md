# AGENTS.md

## Academy Management System — Development Rules

This file defines the permanent development rules and engineering conventions for AI coding agents working on this project.

Read this file before making any code changes.

Phase-specific requirements belong in the relevant task prompt and project documentation, not in this file.

---

# 1. Project Development Mode

The project is currently in **active development**.

At this stage:

* Development speed is highly important.
* Low unnecessary token usage is preferred.
* Prefer simple, practical implementations.
* Avoid unnecessary abstractions.
* Avoid premature optimization.
* Avoid implementing hypothetical future requirements.
* Do not over-engineer features merely because they may be useful someday.
* Reasonable technical debt is acceptable during active development.

When the project approaches a stable v1 release, quality, robustness, security, testing, and backward compatibility requirements will become stricter.

Future requirements should influence architecture only when they can be supported without unnecessary complexity.

---

# 2. Agent Autonomy

The project uses a **controlled autonomous development model**.

Agents are expected to make reasonable technical decisions independently within the established project rules.

Agents may:

* choose implementation details
* refactor code when appropriate
* introduce reasonable abstractions
* add required dependencies
* modify the database schema
* improve existing code
* fix bugs discovered during implementation
* adjust the architecture when necessary

Agents must ask the project owner before making decisions involving:

* unclear business rules
* major product behavior
* ambiguous requirements
* significant architectural changes with broad impact
* decisions where multiple valid approaches would materially affect the product

When a small technical decision is unambiguous, do not stop unnecessarily for approval.

---

# 3. Architecture

The project uses a **Modular Monolith** architecture.

The current architectural structure is based on:

```text
app/
├── domain/
├── application/
├── infrastructure/
└── interface/
```

Follow the existing architecture.

The intended dependency direction is:

```text
Interface
    ↓
Application
    ↓
Domain

Infrastructure → implements infrastructure concerns and interfaces
```

Domain logic must remain independent from infrastructure and framework-specific concerns whenever reasonably practical.

Do not introduce microservices.

Do not split the application into separate deployable services unless explicitly requested.

Do not replace the established architecture without a strong technical reason.

However, architecture is not immutable. If the current architecture proves inadequate, an agent may improve or change it when necessary.

Major architectural changes should be clearly documented.

---

# 4. Domain and Business Logic

Business rules belong in appropriate domain/application components rather than being scattered across route handlers or templates.

Avoid putting substantial business logic directly inside:

* Flask route functions
* Jinja templates
* SQLAlchemy model methods when the logic belongs to a domain/application service
* JavaScript used only as a workaround for missing backend logic

Keep responsibilities clear.

Do not create abstractions solely for theoretical future requirements.

---

# 5. Database

The project uses:

* SQLAlchemy 2.x
* Flask-SQLAlchemy
* Flask-Migrate
* PostgreSQL as the intended production database
* SQLite where appropriate for development/testing

Database models should represent the domain appropriately.

When changing the database schema:

1. Modify the model.
2. Create the required migration.
3. Apply the migration when appropriate.
4. Test the resulting schema.
5. Include migration changes in the Git commit.

Migrations are part of the project history.

Do not casually delete or rewrite existing migrations.

During active development, backward compatibility with old development data is not a primary concern.

Schema changes may be made when they improve the design.

---

# 6. Dependencies

Agents may add a new dependency when it is genuinely useful or necessary.

When adding a dependency:

* add it to the appropriate requirements file
* use a sensible version constraint
* avoid dependencies for trivial functionality that can be implemented simply with the existing stack
* mention significant new dependencies in the final report

Do not add libraries merely because they are popular.

Prefer the existing technology stack when it is sufficient.

---

# 7. Testing

New functionality must have appropriate automated tests.

Tests should cover behavior rather than implementation details.

Use:

* unit tests where appropriate
* integration tests where appropriate
* application/database tests where necessary

There is no mandatory numeric test coverage target during active development.

Before considering a task complete:

* relevant tests must pass
* existing tests must not be unnecessarily broken

Do not remove tests merely to make the test suite pass.

If an existing test becomes invalid because of an intentional behavior change, update the test accordingly.

---

# 8. Code Quality

Use the project's configured Ruff linting and formatting.

Before completing a meaningful task:

```text
ruff check .
ruff format .
```

Fix relevant issues introduced by the task.

Do not perform large unrelated formatting or cleanup operations unless necessary.

Prefer readable and maintainable code over clever code.

---

# 9. Refactoring

Small and directly related refactoring is encouraged.

For example:

```text
Implement feature
    ↓
Discover duplicated or clearly problematic code
    ↓
Small refactor
    ↓
Continue implementation
```

Large architectural refactors should not be silently mixed into an unrelated feature.

If a large refactor is necessary to implement the current feature correctly, explain it clearly in the final report and document important architectural decisions.

---

# 10. Security

Follow sensible security practices from the beginning.

At minimum:

* never store plaintext passwords
* never commit secrets
* keep sensitive configuration in environment variables
* validate user input
* use appropriate authorization checks
* protect web forms against CSRF where applicable
* do not expose sensitive data through APIs or templates
* do not enable development/debug settings in production configuration

Do not over-engineer security infrastructure during active development.

Security requirements will become stricter before stable v1.

---

# 11. Frontend

The current frontend stack is:

```text
Flask
Jinja2
HTML
CSS
Vanilla JavaScript
```

The UI should be:

* Persian
* RTL
* responsive
* mobile-friendly
* practical and functional

Avoid introducing a frontend framework unless explicitly decided later.

Do not build overly complex frontend infrastructure for simple interactions.

Keep frontend code organized and separated from templates where appropriate.

---

# 12. Language Rules

### Source code

Use English for:

* variable names
* function names
* class names
* module names
* database field names
* enum values
* code comments

### Documentation

Project documentation must be written in English.

### Git

Commit messages must be written in English.

### User Interface

User-facing UI text should be Persian and RTL unless a feature explicitly requires another language.

---

# 13. Documentation

Documentation is part of the implementation.

Keep important project knowledge documented so that future developers or agents can understand the system without reading the entire codebase.

Important documentation includes:

```text
README.md
docs/ARCHITECTURE.md
docs/DEVELOPMENT.md
docs/PROJECT_STATUS.md
docs/TODO.md
docs/CHANGELOG.md
docs/adr/
```

Create a dedicated documentation file for a subsystem only when it provides meaningful value.

Do not create unnecessary documentation files.

After completing a meaningful feature or phase:

* update relevant documentation
* update project status
* update TODO status
* update changelog when appropriate

Documentation should explain important decisions and system behavior, not repeat obvious implementation details.

---

# 14. TODO and Project Status

`docs/TODO.md` is the project's high-level roadmap.

It tracks:

* completed phases
* current phase
* future phases
* major planned features

Do not turn TODO.md into a detailed dump of every implementation task.

`docs/PROJECT_STATUS.md` should describe the current state of the project.

After completing a phase:

1. Mark the appropriate TODO items complete.
2. Update PROJECT_STATUS.md.
3. Record important changes in CHANGELOG.md.
4. Commit the completed work.

---

# 15. Phase Boundaries

Development is organized into phases.

An agent must work within the scope of the current phase.

Do not automatically implement future phases.

If the current feature requires a small dependency from a future area, implement only what is necessary.

If the agent discovers work belonging to a later phase:

* do not implement it automatically
* record or report it when appropriate
* leave the future phase for its designated task

The project owner controls when the next phase begins.

---

# 16. Git Workflow

Git is mandatory for the project.

The repository is initialized during project bootstrap.

Agents must preserve the existing Git history.

Before meaningful changes:

```bash
git status
git log -n 5
```

After completing a meaningful feature/task:

1. Run relevant tests.
2. Run Ruff linting.
3. Run Ruff formatting.
4. Review the diff.
5. Verify no secrets or unrelated changes were introduced.
6. Update relevant documentation.
7. Commit the completed work.

Use clear English commit messages.

Example:

```text
feat: implement course management
```

or:

```text
fix: correct session rescheduling
```

Do not rewrite Git history.

Do not use destructive Git commands such as resetting or deleting work without explicit authorization.

Keep the working tree clean after completing a task.

---

# 17. Commit Granularity

A commit should represent a meaningful logical unit of work.

Prefer:

```text
Feature implementation
+ relevant tests
+ relevant documentation
→ one logical commit
```

Do not create a separate commit for every file.

Do not create dozens of tiny commits for trivial changes.

If a feature naturally consists of several independent logical units, multiple commits are acceptable.

---

# 18. API

The project exposes an API namespace:

```text
/api/v1/
```

Keep the API architecture available for future clients, including mobile applications.

Do not implement API endpoints merely because they might be useful in the future.

Build APIs when required by an actual feature or client.

Follow the existing application/domain architecture rather than putting business logic directly inside API handlers.

---

# 19. Mobile Readiness

The project is primarily developed as a web application.

Future mobile applications may consume the API.

Therefore:

* keep domain logic independent from the web interface
* avoid coupling business logic to Jinja templates
* keep API boundaries clean
* avoid assumptions that only make sense for browser-based clients

Do not build a mobile application or mobile-specific infrastructure during ordinary web development unless explicitly requested.

---

# 20. File Storage

The application may need to store:

* profile images
* homework files
* educational resources
* payment receipts
* other user-uploaded files

The current approach may use local server storage.

Design file-related code so that storage can be replaced by object storage later if necessary.

Do not implement cloud/object storage infrastructure unless required.

Validate uploaded files appropriately.

---

# 21. Financial Data

Financial data is important and must be treated as historical records.

The financial system should use a transaction/ledger-oriented model rather than relying only on a mutable balance field.

When implementing financial features:

* preserve transaction history
* avoid destructive modification of financial history
* use explicit correction/reversal mechanisms where appropriate
* use appropriate numeric types for monetary values
* keep the currency definition consistent

The current project currency is **Toman**.

Detailed financial business rules belong to the relevant finance phase and should not be invented here.

---

# 22. Dates and Time

Use proper database date/time types for canonical stored values.

Do not store formatted display dates as the canonical database value.

The application UI may display dates in Persian/Jalali format.

When implementing scheduling or session functionality, carefully distinguish between:

* stored date/time
* displayed Persian/Jalali date
* recurring weekly schedule
* individual session exceptions

Do not invent scheduling rules without a product decision when the behavior affects business logic.

---

# 23. Error Handling

Handle expected errors explicitly.

User-facing errors should be understandable and appropriate for the Persian UI.

Do not expose stack traces, secrets, SQL queries, or internal implementation details to users.

Development environments may provide more detailed debugging information.

Production configuration must remain appropriately restricted.

---

# 24. Performance

During active development:

* prioritize correctness and development speed
* avoid premature optimization
* do not optimize hypothetical bottlenecks
* prefer simple database queries and clear code

However, avoid obviously inefficient patterns when the correct implementation is equally simple.

Performance optimization will become more important as the project approaches stable v1 and real-world usage.

---

# 25. Scope Discipline

Before implementing a task:

1. Understand the requested scope.
2. Inspect the relevant existing code.
3. Identify dependencies.
4. Implement the smallest complete solution.
5. Test it.
6. Document it where appropriate.
7. Commit it.

Do not turn a feature request into an unrelated rewrite of the project.

Do not modify unrelated files without a reason.

---

# 26. Handling Ambiguity

When requirements are ambiguous:

### Make the decision yourself when:

* the decision is a small technical implementation detail
* one option is clearly consistent with the architecture
* the decision does not materially affect product behavior

### Ask the project owner when:

* business behavior is unclear
* multiple reasonable product behaviors exist
* the decision affects important data structures
* the decision significantly affects architecture
* the decision could create difficult future constraints

Do not stop development for trivial questions.

---

# 27. Existing Code and Data

Before changing existing functionality:

* inspect the current implementation
* understand its purpose
* preserve useful behavior
* avoid unnecessary rewrites

The project is currently in active development.

Compatibility with old development data is not a major constraint.

When a cleaner schema or architecture is justified, it may replace an earlier development implementation.

Before stable v1, database migrations and compatibility requirements may become stricter.

---

# 28. Agent Completion Report

At the end of every meaningful task, provide a concise report containing:

```text
## Completed
## Files Changed
## Tests
## Lint / Format
## Database / Migration
## Documentation
## Git Commit
## Important Decisions
## Issues / Unresolved Items
## Recommended Next Step
```

Do not claim something was completed without verifying it.

Do not automatically begin the next phase.

---

# 29. Definition of Done

A meaningful feature is considered complete when:

* the requested functionality is implemented
* relevant tests pass
* Ruff passes
* relevant database migrations exist and work
* relevant documentation is updated
* TODO/PROJECT_STATUS are updated when appropriate
* changes have been reviewed
* a Git commit has been created
* the working tree is clean

The exact Definition of Done may be extended by a phase-specific task.

---

# 30. Priority Order

When making engineering decisions, generally prioritize:

```text
1. Correct product behavior
2. Simplicity
3. Maintainability
4. Development speed
5. Reasonable future extensibility
6. Performance optimization
```

Do not sacrifice current correctness for hypothetical future requirements.

Do not sacrifice simplicity merely to make the system theoretically extensible.

The goal is a clean, practical, maintainable system that can evolve as the academy's real requirements become clearer.
