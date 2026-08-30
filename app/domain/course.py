from __future__ import annotations


class Course:
    """Course domain entity.

    Represents a reusable educational program/template offered by the academy.
    A Course is NOT an actual class — it's the template from which classes are created.
    """

    def __init__(
        self,
        id: int | None,
        title: str,
        description: str = "",
        num_sessions: int = 1,
        min_age: int | None = None,
        max_age: int | None = None,
        prerequisites: str = "",
    ):
        self.id = id
        self.title = title
        self.description = description
        self.num_sessions = num_sessions
        self.min_age = min_age
        self.max_age = max_age
        self.prerequisites = prerequisites

    def __repr__(self) -> str:
        return f"<Course id={self.id} title={self.title!r}>"


class SyllabusItem:
    """Syllabus item domain entity.

    Represents planned content for a specific session/order within a Course.
    """

    def __init__(
        self,
        id: int | None,
        course_id: int,
        order: int,
        title: str,
        description: str = "",
        homework: str = "",
        assessment: str = "",
    ):
        self.id = id
        self.course_id = course_id
        self.order = order
        self.title = title
        self.description = description
        self.homework = homework
        self.assessment = assessment

    def __repr__(self) -> str:
        return f"<SyllabusItem id={self.id} order={self.order} title={self.title!r}>"
