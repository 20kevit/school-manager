# ADR-003: Application Factory Pattern

## Context

Flask applications need a flexible way to create instances for different environments (development, testing, production) and to support testing.

## Decision

Use Flask's **Application Factory** pattern via `create_app(config_name)`.

## Consequences

**Positive:**
- Multiple configurations (dev, test, prod).
- Easy to create fresh app instances for testing.
- Extensions initialized cleanly.
- Follows Flask best practices.

**Negative:**
- Slightly more code upfront than a simple global app object.

## Alternatives Considered

- **Global app object**: Simpler but prevents testing with different configs.
- **Module-level app**: Same limitation; harder to test.

## References

- Flask documentation: Application Factories
