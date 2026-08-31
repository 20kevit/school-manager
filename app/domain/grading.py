from __future__ import annotations

from datetime import datetime


class GradingTemplate:
    """GradingTemplate domain entity.

    Defines the weight distribution for different assessment types
    within a class. Used to calculate weighted final grades.
    """

    def __init__(
        self,
        id: int | None,
        class_id: int,
        title: str,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.class_id = class_id
        self.title = title
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def __repr__(self) -> str:
        return (
            f"<GradingTemplate id={self.id} class={self.class_id} title={self.title!r}>"
        )


class GradingComponent:
    """GradingComponent domain entity.

    A single weight component within a GradingTemplate.
    Maps an assessment type to its weight percentage.
    """

    def __init__(
        self,
        id: int | None,
        template_id: int,
        assessment_type: str,
        weight: float,
    ):
        self.id = id
        self.template_id = template_id
        self.assessment_type = assessment_type
        self.weight = weight

    def __repr__(self) -> str:
        return (
            f"<GradingComponent id={self.id} template={self.template_id} "
            f"type={self.assessment_type!r} weight={self.weight}>"
        )
