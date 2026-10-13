"""Safe user-facing error reporting for web routes.

Internal exception text (SQLAlchemy errors, filesystem paths, provider
payloads) must never reach the UI: it leaks schema and infrastructure
details. Log the exception server-side with a traceback and show the user
a generic, actionable Persian message instead.
"""

from __future__ import annotations

import logging

from flask import flash

logger = logging.getLogger(__name__)

GENERIC_ERROR_MESSAGE = "خطایی رخ داد. لطفاً دوباره تلاش کنید."


def flash_safe_error(exc: BaseException, message: str = GENERIC_ERROR_MESSAGE) -> None:
    """Log an exception with traceback; flash a generic message to the user."""
    logger.exception("Handled web error: %s", type(exc).__name__)
    flash(message, "error")
