# ADR-001: Modular Monolith Architecture

## Context

We need an architecture for the Academy Management System that balances simplicity with long-term maintainability. The system must support web and future API/mobile clients, multiple domains (students, teachers, finance, etc.), and eventual integration with external services.

## Decision

Use a **modular monolith** architecture with four layers:

- **Domain**: Business entities and rules.
- **Application**: Use case orchestration.
- **Infrastructure**: Database, external services.
- **Interface**: Web routes, API endpoints.

Dependency direction: Interface -> Application -> Domain, with Infrastructure implementing domain contracts.

## Consequences

**Positive:**
- Clear separation of concerns without microservice complexity.
- Easy to test domain logic independently.
- Can evolve toward services if needed.
- Simple deployment.

**Negative:**
- Requires discipline to maintain layer boundaries.
- All code deploys together.

## Alternatives Considered

- **Microservices**: Too complex for current scale; premature.
- **Flat structure**: Leads to tangled code over time.
- **Domain-driven design (full)**: Too heavy for initial implementation.

## References

- [Modular Monolith](https://www.thereformedprogrammer.net/domain-driven-design-for-beginners/)
- Flask documentation: Application Factory Pattern
