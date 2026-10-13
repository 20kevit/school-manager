"""PostgreSQL-only concurrency primitives.

These helpers make multi-step financial transitions safe under concurrent
requests on PostgreSQL, while remaining deterministic no-ops on SQLite
(where the test suite runs). Every function degrades gracefully when no
bind/dialect information is available.
"""

from __future__ import annotations

from sqlalchemy import text as sa_text


def is_postgresql(session) -> bool:
    """True only when the session is bound to a PostgreSQL database."""
    try:
        bind = session.bind
        return bind is not None and bind.dialect.name == "postgresql"
    except Exception:
        return False


def pg_advisory_xact_lock(session, key: str) -> None:
    """Take a transaction-scoped advisory lock (PostgreSQL only).

    Serializes a validate-then-insert unit across concurrent transactions:
    the second transaction blocks here until the first commits or rolls
    back, so its subsequent validation observes committed state. The lock
    is released automatically at transaction end. No-op on other backends.
    """
    if not is_postgresql(session):
        return
    session.execute(
        sa_text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": key}
    )


def with_for_update_if_pg(query):
    """Add SELECT ... FOR UPDATE on PostgreSQL; return query unchanged elsewhere."""
    try:
        bind = query.session.bind
        if bind is not None and bind.dialect.name == "postgresql":
            return query.with_for_update()
    except Exception:
        pass
    return query
