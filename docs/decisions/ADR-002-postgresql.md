# ADR-002: PostgreSQL as Primary Database

## Context

The system needs a reliable, production-grade relational database. Data includes student records, financial transactions, and relationships between entities.

## Decision

Use **PostgreSQL** as the primary database in production.

## Consequences

**Positive:**
- ACID compliance for financial data.
- Rich type system (JSON, arrays, etc.).
- Excellent Python ecosystem (psycopg2, SQLAlchemy).
- Strong migration support (Alembic).

**Negative:**
- Requires a running PostgreSQL server (unlike SQLite for dev).
- Heavier than SQLite for simple local development.

## Alternatives Considered

- **SQLite**: Not suitable for production or concurrent access.
- **MySQL**: Viable, but PostgreSQL has richer features.
- **MongoDB**: Schema-less; not appropriate for relational data.
