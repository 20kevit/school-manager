from enum import StrEnum


class Role(StrEnum):
    """User roles in the academy system."""

    ADMIN = "ADMIN"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"
    PARENT = "PARENT"
