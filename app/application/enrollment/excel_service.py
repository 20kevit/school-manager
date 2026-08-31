"""Excel import/export service for student bulk operations."""

from __future__ import annotations

import io
from dataclasses import dataclass, field

import openpyxl

from app.extensions import db
from app.infrastructure.database.models import (
    RoleModel,
    StudentProfileModel,
    UserModel,
)
from app.utils.date_utils import parse_jalali_date


class ExcelImportError(Exception):
    """Raised when Excel import fails."""


@dataclass
class ImportRowResult:
    """Result for a single row import."""

    row_number: int
    national_id: str
    status: str  # "created", "duplicate", "linked", "error"
    message: str = ""


@dataclass
class ImportResult:
    """Result of an Excel import operation."""

    total_rows: int = 0
    created: int = 0
    duplicates: int = 0
    linked: int = 0
    errors: int = 0
    rows: list[ImportRowResult] = field(default_factory=list)


REQUIRED_COLUMNS = {
    "first_name",
    "last_name",
    "national_id",
    "mobile_phone",
    "birth_date",
}

COLUMN_MAP = {
    "first_name": "first_name",
    "last_name": "last_name",
    "national_id": "national_id",
    "mobile_phone": "mobile_phone",
    "birth_date": "birth_date",
    "gender": "gender",
}


def parse_excel_file(file_content: bytes) -> ImportResult:
    """Parse an Excel file and import students.

    Expected columns: first_name, last_name, national_id, mobile_phone,
    birth_date (Jalali format YYYY/MM/DD), gender (optional).

    Logic:
    - Reads each row from the first worksheet.
    - Validates required columns exist.
    - For each row:
        - If national_id already exists as a StudentProfile, skip (duplicate).
        - If new, create UserModel (inactive, password=national_id),
          assign STUDENT role, create StudentProfileModel.
    - Returns ImportResult with counts and per-row details.
    """
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True)
    except Exception as e:
        raise ExcelImportError(f"Cannot read Excel file: {e}")

    ws = wb.active
    if ws is None:
        raise ExcelImportError("Excel file has no worksheets.")

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        raise ExcelImportError(
            "Excel file must have a header row and at least one data row."
        )

    header = [str(cell).strip().lower() if cell else "" for cell in rows[0]]
    header_map = {}
    for idx, col_name in enumerate(header):
        normalized = col_name.replace(" ", "_").replace("-", "_")
        if normalized in COLUMN_MAP:
            header_map[COLUMN_MAP[normalized]] = idx

    missing = REQUIRED_COLUMNS - set(header_map.keys())
    if missing:
        raise ExcelImportError(
            f"Missing required columns: {', '.join(sorted(missing))}"
        )

    result = ImportResult()

    for row_idx, row in enumerate(rows[1:], start=2):
        if all(cell is None for cell in row):
            continue

        result.total_rows += 1

        try:
            national_id = _get_cell(row, header_map["national_id"])
            first_name = _get_cell(row, header_map["first_name"])
            last_name = _get_cell(row, header_map["last_name"])
            mobile_phone = _get_cell(row, header_map["mobile_phone"])
            birth_date_str = _get_cell(row, header_map["birth_date"])
            gender = (
                _get_cell(row, header_map.get("gender"))
                if "gender" in header_map
                else "MALE"
            )

            if (
                not national_id
                or not first_name
                or not last_name
                or not mobile_phone
                or not birth_date_str
            ):
                result.errors += 1
                result.rows.append(
                    ImportRowResult(
                        row_number=row_idx,
                        national_id=national_id or "",
                        status="error",
                        message="Missing required fields.",
                    )
                )
                continue

            existing_profile = StudentProfileModel.query.filter_by(
                national_id=national_id
            ).first()
            if existing_profile is not None:
                result.duplicates += 1
                result.rows.append(
                    ImportRowResult(
                        row_number=row_idx,
                        national_id=national_id,
                        status="duplicate",
                        message="Student with this national ID already exists.",
                    )
                )
                continue

            birth_date = parse_jalali_date(birth_date_str)

            user = UserModel(login=national_id)
            user.set_password(national_id)
            db.session.add(user)
            db.session.flush()

            student_role = RoleModel.query.get("STUDENT")
            if student_role is None:
                student_role = RoleModel(name="STUDENT")
                db.session.add(student_role)
                db.session.flush()
            user.roles.append(student_role)

            profile = StudentProfileModel(
                user_id=user.id,
                first_name=first_name,
                last_name=last_name,
                national_id=national_id,
                mobile_phone=mobile_phone,
                birth_date=birth_date,
                gender=gender or "MALE",
            )
            db.session.add(profile)
            db.session.flush()

            result.created += 1
            result.rows.append(
                ImportRowResult(
                    row_number=row_idx,
                    national_id=national_id,
                    status="created",
                    message=f"User created: {national_id}",
                )
            )

        except Exception as e:
            result.errors += 1
            result.rows.append(
                ImportRowResult(
                    row_number=row_idx,
                    national_id="",
                    status="error",
                    message=str(e),
                )
            )

    db.session.commit()
    wb.close()
    return result


def export_students_to_excel(
    students: list | None = None,
) -> bytes:
    """Export student list to an Excel file.

    If students is None, exports all students.
    Returns the Excel file content as bytes.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Students"

    headers = [
        "first_name",
        "last_name",
        "national_id",
        "mobile_phone",
        "birth_date",
        "gender",
    ]
    ws.append(headers)

    if students is None:
        students = StudentProfileModel.query.all()

    for profile in students:
        ws.append(
            [
                profile.first_name,
                profile.last_name,
                profile.national_id,
                profile.mobile_phone,
                profile.birth_date.strftime("%Y/%m/%d") if profile.birth_date else "",
                profile.gender or "",
            ]
        )

    output = io.BytesIO()
    wb.save(output)
    wb.close()
    return output.getvalue()


def _get_cell(row: tuple, col_idx: int | None) -> str:
    """Get a cell value as a stripped string."""
    if col_idx is None or col_idx >= len(row):
        return ""
    val = row[col_idx]
    if val is None:
        return ""
    return str(val).strip()
