from __future__ import annotations

from datetime import date, time
from enum import StrEnum


class SessionStatus(StrEnum):
    """Status of an individual session."""

    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Session:
    """Session domain entity.

    Represents an individual occurrence of a class session.
    Persisted records — not dynamically calculated.
    """

    def __init__(
        self,
        id: int | None,
        class_id: int,
        session_number: int,
        scheduled_date: date,
        start_time: time,
        end_time: time,
        status: SessionStatus = SessionStatus.SCHEDULED,
        title: str | None = None,
        description: str | None = None,
        is_rescheduled: bool = False,
    ):
        self.id = id
        self.class_id = class_id
        self.session_number = session_number
        self.scheduled_date = scheduled_date
        self.start_time = start_time
        self.end_time = end_time
        self.status = status
        self.title = title
        self.description = description
        self.is_rescheduled = is_rescheduled

    def __repr__(self) -> str:
        return (
            f"<Session id={self.id} class={self.class_id} "
            f"num={self.session_number} date={self.scheduled_date}>"
        )
