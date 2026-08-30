from __future__ import annotations

from app.extensions import db
from app.infrastructure.database.models import CourseModel, SyllabusItemModel


class CourseError(Exception):
    """Raised when a course operation fails."""


def create_course(
    title: str,
    description: str = "",
    num_sessions: int = 1,
    min_age: int | None = None,
    max_age: int | None = None,
    prerequisites: str = "",
) -> CourseModel:
    """Create a new course."""
    if not title or not title.strip():
        raise CourseError("Course title is required.")
    if num_sessions < 1:
        raise CourseError("Number of sessions must be at least 1.")
    if min_age is not None and max_age is not None and min_age > max_age:
        raise CourseError("Minimum age cannot be greater than maximum age.")

    course = CourseModel(
        title=title.strip(),
        description=description.strip(),
        num_sessions=num_sessions,
        min_age=min_age,
        max_age=max_age,
        prerequisites=prerequisites.strip(),
    )
    db.session.add(course)
    db.session.commit()
    return course


def update_course(
    course: CourseModel,
    title: str | None = None,
    description: str | None = None,
    num_sessions: int | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    prerequisites: str | None = None,
) -> CourseModel:
    """Update an existing course."""
    if title is not None:
        if not title.strip():
            raise CourseError("Course title cannot be empty.")
        course.title = title.strip()
    if description is not None:
        course.description = description.strip()
    if num_sessions is not None:
        if num_sessions < 1:
            raise CourseError("Number of sessions must be at least 1.")
        course.num_sessions = num_sessions
    if min_age is not None:
        course.min_age = min_age
    if max_age is not None:
        course.max_age = max_age
    if prerequisites is not None:
        course.prerequisites = prerequisites.strip()

    db.session.commit()
    return course


def get_course(course_id: int) -> CourseModel | None:
    """Get a course by ID."""
    return CourseModel.query.get(course_id)


def list_courses() -> list[CourseModel]:
    """List all courses."""
    return CourseModel.query.order_by(CourseModel.title).all()


def delete_course(course: CourseModel) -> None:
    """Delete a course."""
    db.session.delete(course)
    db.session.commit()


# ---------------------------------------------------------------------------
# Syllabus
# ---------------------------------------------------------------------------


def add_syllabus_item(
    course: CourseModel,
    order: int,
    title: str,
    description: str = "",
    homework: str = "",
    assessment: str = "",
) -> SyllabusItemModel:
    """Add a syllabus item to a course."""
    if not title or not title.strip():
        raise CourseError("Syllabus item title is required.")
    if order < 1:
        raise CourseError("Order must be at least 1.")

    existing = SyllabusItemModel.query.filter_by(
        course_id=course.id, order=order
    ).first()
    if existing:
        raise CourseError(f"Syllabus item with order {order} already exists.")

    item = SyllabusItemModel(
        course_id=course.id,
        order=order,
        title=title.strip(),
        description=description.strip(),
        homework=homework.strip(),
        assessment=assessment.strip(),
    )
    db.session.add(item)
    db.session.commit()
    return item


def update_syllabus_item(
    item: SyllabusItemModel,
    title: str | None = None,
    description: str | None = None,
    homework: str | None = None,
    assessment: str | None = None,
    order: int | None = None,
) -> SyllabusItemModel:
    """Update a syllabus item."""
    if title is not None:
        if not title.strip():
            raise CourseError("Syllabus item title cannot be empty.")
        item.title = title.strip()
    if description is not None:
        item.description = description.strip()
    if homework is not None:
        item.homework = homework.strip()
    if assessment is not None:
        item.assessment = assessment.strip()
    if order is not None:
        if order < 1:
            raise CourseError("Order must be at least 1.")
        existing = SyllabusItemModel.query.filter_by(
            course_id=item.course_id, order=order
        ).first()
        if existing and existing.id != item.id:
            raise CourseError(f"Syllabus item with order {order} already exists.")
        item.order = order

    db.session.commit()
    return item


def delete_syllabus_item(item: SyllabusItemModel) -> None:
    """Delete a syllabus item."""
    db.session.delete(item)
    db.session.commit()


def get_syllabus_items(course_id: int) -> list[SyllabusItemModel]:
    """Get all syllabus items for a course, ordered."""
    return (
        SyllabusItemModel.query.filter_by(course_id=course_id)
        .order_by(SyllabusItemModel.order)
        .all()
    )
