"""Centralized Persian (Jalali/Shamsi) date utilities.

Storage: Gregorian (date/datetime) in the database.
Display/Input: Persian (Jalali) in the UI.

This module provides conversion, formatting, and parsing utilities.
"""

from __future__ import annotations

from datetime import date, datetime, time

import jdatetime


def gregorian_to_jalali(
    d: date | datetime | None,
) -> jdatetime.date | jdatetime.datetime | None:
    """Convert a Gregorian date or datetime to Jalali."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return jdatetime.datetime.fromgregorian(datetime=d)
    return jdatetime.date.fromgregorian(date=d)


def jalali_to_gregorian(
    jd: jdatetime.date | jdatetime.datetime | None,
) -> date | datetime | None:
    """Convert a Jalali date or datetime to Gregorian."""
    if jd is None:
        return None
    if isinstance(jd, jdatetime.datetime):
        return jd.togregorian()
    return jd.togregorian()


def format_jalali(d: date | datetime | None, fmt: str = "%Y/%m/%d") -> str:
    """Format a Gregorian date/datetime as a Persian date string.

    Default format: 1405/06/10 (Jalali).
    """
    if d is None:
        return "—"
    jd = gregorian_to_jalali(d)
    if jd is None:
        return "—"
    return jd.strftime(fmt)


def format_jalali_datetime(dt: datetime | None) -> str:
    """Format a Gregorian datetime as Persian date + time.

    Output: 1405/06/10 17:30
    """
    if dt is None:
        return "—"
    return format_jalali(dt, "%Y/%m/%d %H:%M")


def format_jalali_time(t: time | None) -> str:
    """Format a time object as HH:MM."""
    if t is None:
        return "—"
    return t.strftime("%H:%M")


def format_jalali_date_input(d: date | None) -> str:
    """Format a Gregorian date for use in form inputs (Jalali YYYY/MM/DD).

    Returns empty string for None.
    """
    if d is None:
        return ""
    return format_jalali(d, "%Y/%m/%d")


def parse_jalali_date(value: str) -> date:
    """Parse a Jalali date string (YYYY/MM/DD) and return Gregorian date.

    Supports both '/' and '-' separators.
    Raises ValueError if the input is invalid.
    """
    if not value or not value.strip():
        raise ValueError("تاریخ الزامی است.")
    parts = value.strip().replace("-", "/").split("/")
    if len(parts) != 3:
        raise ValueError("فرمت تاریخ نامعتبر است. فرمت صحیح: ۱۴۰۵/۰۶/۱۰")
    try:
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        raise ValueError("فرمت تاریخ نامعتبر است. فرمت صحیح: ۱۴۰۵/۰۶/۱۰")
    try:
        jd = jdatetime.date(year, month, day)
    except ValueError:
        raise ValueError("تاریخ شمسی نامعتبر است. لطفاً تاریخ صحیح را وارد کنید.")
    return jd.togregorian()


def parse_jalali_datetime(value: str) -> datetime:
    """Parse a Jalali datetime string (YYYY/MM/DD HH:MM) and return Gregorian datetime.

    Raises ValueError if the input is invalid.
    """
    if not value or not value.strip():
        raise ValueError("تاریخ و ساعت الزامی است.")
    parts = value.strip().split(" ", 1)
    if len(parts) != 2:
        raise ValueError("فرمت تاریخ و ساعت نامعتبر است. فرمت صحیح: ۱۴۰۵/۰۶/۱۰ ۱۴:۳۰")
    date_result = parse_jalali_date(parts[0])
    time_parts = parts[1].split(":")
    if len(time_parts) != 2:
        raise ValueError("فرمت ساعت نامعتبر است. فرمت صحیح: ۱۴:۳۰")
    try:
        hours, minutes = int(time_parts[0]), int(time_parts[1])
    except ValueError:
        raise ValueError("فرمت ساعت نامعتبر است.")
    return datetime(
        date_result.year, date_result.month, date_result.day, hours, minutes
    )


def parse_jalali_date_or_none(value: str) -> date | None:
    """Parse a Jalali date string, returning None for empty/blank values."""
    if not value or not value.strip():
        return None
    return parse_jalali_date(value)


def compute_age(birth_date: date) -> int:
    """Compute age from a birth date (Gregorian)."""
    today = date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def compute_age_jalali(birth_date: date) -> int:
    """Compute age, ignoring Jalali conversion (age is calendar-agnostic)."""
    return compute_age(birth_date)
