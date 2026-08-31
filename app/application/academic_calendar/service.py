from __future__ import annotations

from datetime import date

from app.extensions import db
from app.infrastructure.database.models import (
    AcademicCalendarEventModel,
    AcademicYearModel,
    SemesterModel,
)


class AcademicCalendarError(Exception):
    """Raised when an academic calendar operation fails."""


# ---------------------------------------------------------------------------
# Academic Year CRUD
# ---------------------------------------------------------------------------


def create_academic_year(
    title: str,
    start_date: date,
    end_date: date,
    is_active: bool = False,
) -> AcademicYearModel:
    if not title or not title.strip():
        raise AcademicCalendarError("Title is required.")
    if start_date >= end_date:
        raise AcademicCalendarError("Start date must be before end date.")
    if is_active:
        AcademicYearModel.query.update({AcademicYearModel.is_active: False})

    year = AcademicYearModel(
        title=title.strip(),
        start_date=start_date,
        end_date=end_date,
        is_active=is_active,
    )
    db.session.add(year)
    db.session.commit()
    return year


def update_academic_year(
    year: AcademicYearModel,
    title: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    is_active: bool | None = None,
) -> AcademicYearModel:
    if title is not None:
        if not title.strip():
            raise AcademicCalendarError("Title cannot be empty.")
        year.title = title.strip()
    if start_date is not None:
        year.start_date = start_date
    if end_date is not None:
        year.end_date = end_date
    if year.start_date >= year.end_date:
        raise AcademicCalendarError("Start date must be before end date.")
    if is_active is not None:
        if is_active:
            AcademicYearModel.query.update({AcademicYearModel.is_active: False})
        year.is_active = is_active
    db.session.commit()
    return year


def get_academic_year(year_id: int) -> AcademicYearModel | None:
    return AcademicYearModel.query.get(year_id)


def list_academic_years() -> list[AcademicYearModel]:
    return AcademicYearModel.query.order_by(AcademicYearModel.start_date.desc()).all()


def delete_academic_year(year: AcademicYearModel) -> None:
    db.session.delete(year)
    db.session.commit()


# ---------------------------------------------------------------------------
# Semester CRUD
# ---------------------------------------------------------------------------


def create_semester(
    academic_year_id: int,
    title: str,
    start_date: date,
    end_date: date,
    is_active: bool = False,
) -> SemesterModel:
    if not title or not title.strip():
        raise AcademicCalendarError("Title is required.")
    year = AcademicYearModel.query.get(academic_year_id)
    if year is None:
        raise AcademicCalendarError("Academic year not found.")
    if start_date >= end_date:
        raise AcademicCalendarError("Start date must be before end date.")
    if is_active:
        SemesterModel.query.update({SemesterModel.is_active: False})

    semester = SemesterModel(
        academic_year_id=academic_year_id,
        title=title.strip(),
        start_date=start_date,
        end_date=end_date,
        is_active=is_active,
    )
    db.session.add(semester)
    db.session.commit()
    return semester


def update_semester(
    semester: SemesterModel,
    title: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    is_active: bool | None = None,
) -> SemesterModel:
    if title is not None:
        if not title.strip():
            raise AcademicCalendarError("Title cannot be empty.")
        semester.title = title.strip()
    if start_date is not None:
        semester.start_date = start_date
    if end_date is not None:
        semester.end_date = end_date
    if semester.start_date >= semester.end_date:
        raise AcademicCalendarError("Start date must be before end date.")
    if is_active is not None:
        if is_active:
            SemesterModel.query.update({SemesterModel.is_active: False})
        semester.is_active = is_active
    db.session.commit()
    return semester


def get_semester(semester_id: int) -> SemesterModel | None:
    return SemesterModel.query.get(semester_id)


def list_semesters(academic_year_id: int | None = None) -> list[SemesterModel]:
    query = SemesterModel.query
    if academic_year_id is not None:
        query = query.filter_by(academic_year_id=academic_year_id)
    return query.order_by(SemesterModel.start_date.desc()).all()


def get_active_semester() -> SemesterModel | None:
    return SemesterModel.query.filter_by(is_active=True).first()


def delete_semester(semester: SemesterModel) -> None:
    db.session.delete(semester)
    db.session.commit()


# ---------------------------------------------------------------------------
# Academic Calendar Event CRUD
# ---------------------------------------------------------------------------


def create_calendar_event(
    title: str,
    start_date: date,
    end_date: date | None = None,
    is_recurring: bool = False,
    description: str = "",
) -> AcademicCalendarEventModel:
    if not title or not title.strip():
        raise AcademicCalendarError("Title is required.")
    if end_date is not None and start_date > end_date:
        raise AcademicCalendarError("Start date must not be after end date.")

    event = AcademicCalendarEventModel(
        title=title.strip(),
        start_date=start_date,
        end_date=end_date,
        is_recurring=is_recurring,
        description=description.strip(),
    )
    db.session.add(event)
    db.session.commit()
    return event


def update_calendar_event(
    event: AcademicCalendarEventModel,
    title: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    is_recurring: bool | None = None,
    description: str | None = None,
) -> AcademicCalendarEventModel:
    if title is not None:
        if not title.strip():
            raise AcademicCalendarError("Title cannot be empty.")
        event.title = title.strip()
    if start_date is not None:
        event.start_date = start_date
    if end_date is not None:
        event.end_date = end_date
    if event.end_date is not None and event.start_date > event.end_date:
        raise AcademicCalendarError("Start date must not be after end date.")
    if is_recurring is not None:
        event.is_recurring = is_recurring
    if description is not None:
        event.description = description.strip()
    db.session.commit()
    return event


def get_calendar_event(event_id: int) -> AcademicCalendarEventModel | None:
    return AcademicCalendarEventModel.query.get(event_id)


def list_calendar_events() -> list[AcademicCalendarEventModel]:
    return AcademicCalendarEventModel.query.order_by(
        AcademicCalendarEventModel.start_date
    ).all()


def delete_calendar_event(event: AcademicCalendarEventModel) -> None:
    db.session.delete(event)
    db.session.commit()


def is_date_holiday(check_date: date) -> bool:
    """Check if a date falls within any calendar event (holiday)."""
    today_events = AcademicCalendarEventModel.query.filter(
        AcademicCalendarEventModel.start_date <= check_date
    ).all()
    for event in today_events:
        effective_end = event.end_date if event.end_date else event.start_date
        if check_date <= effective_end:
            return True
    return False
