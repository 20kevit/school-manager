from __future__ import annotations

from datetime import date


class AcademicYear:
    """Academic year domain entity (e.g., '1403-1404')."""

    def __init__(
        self,
        id: int | None,
        title: str,
        start_date: date,
        end_date: date,
        is_active: bool = False,
    ):
        self.id = id
        self.title = title
        self.start_date = start_date
        self.end_date = end_date
        self.is_active = is_active

    def __repr__(self) -> str:
        return f"<AcademicYear id={self.id} title={self.title!r}>"


class Semester:
    """Semester domain entity (e.g., 'نیم‌سال اول', linked to AcademicYear)."""

    def __init__(
        self,
        id: int | None,
        academic_year_id: int,
        title: str,
        start_date: date,
        end_date: date,
        is_active: bool = False,
    ):
        self.id = id
        self.academic_year_id = academic_year_id
        self.title = title
        self.start_date = start_date
        self.end_date = end_date
        self.is_active = is_active

    def __repr__(self) -> str:
        return f"<Semester id={self.id} title={self.title!r}>"


class AcademicCalendarEvent:
    """Academic calendar event / holiday domain entity."""

    def __init__(
        self,
        id: int | None,
        title: str,
        start_date: date,
        end_date: date | None = None,
        is_recurring: bool = False,
        description: str = "",
    ):
        self.id = id
        self.title = title
        self.start_date = start_date
        self.end_date = end_date
        self.is_recurring = is_recurring
        self.description = description

    def contains_date(self, check_date: date) -> bool:
        """Check if a given date falls within this event's range."""
        end = self.end_date if self.end_date else self.start_date
        return self.start_date <= check_date <= end

    def __repr__(self) -> str:
        return f"<AcademicCalendarEvent id={self.id} title={self.title!r}>"
