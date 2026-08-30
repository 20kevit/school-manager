from functools import wraps

from flask import abort
from flask_login import current_user


def role_required(*role_names: str):
    """Decorator that requires the current user to have at least one of the specified roles.

    Usage:
        @role_required("ADMIN")
        @role_required("ADMIN", "TEACHER")
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not current_user.has_any_role(*role_names):
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator
