from __future__ import annotations

from datetime import date
from enum import StrEnum


class Gender(StrEnum):
    """Gender options for profiles."""

    MALE = "MALE"
    FEMALE = "FEMALE"


class StudentProfile:
    """Student domain entity."""

    def __init__(
        self,
        id: int | None,
        user_id: int,
        first_name: str,
        last_name: str,
        national_id: str,
        mobile_phone: str,
        birth_date: date,
        gender: Gender,
    ):
        self.id = id
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.national_id = national_id
        self.mobile_phone = mobile_phone
        self.birth_date = birth_date
        self.gender = gender


class TeacherProfile:
    """Teacher domain entity."""

    def __init__(
        self,
        id: int | None,
        user_id: int,
        first_name: str,
        last_name: str,
        national_id: str,
        mobile_phone: str,
    ):
        self.id = id
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.national_id = national_id
        self.mobile_phone = mobile_phone


class ParentProfile:
    """Parent domain entity."""

    def __init__(
        self,
        id: int | None,
        user_id: int,
        first_name: str,
        last_name: str,
        national_id: str,
        mobile_phone: str,
    ):
        self.id = id
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.national_id = national_id
        self.mobile_phone = mobile_phone
