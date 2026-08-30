from __future__ import annotations

from datetime import datetime

from app.domain.profiles import ParentProfile, StudentProfile, TeacherProfile
from app.domain.role import Role


class User:
    """User domain entity.

    Represents the authentication account, not a specific academy role.
    """

    def __init__(
        self,
        id: int | None,
        login: str,
        password_hash: str,
        is_active: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.login = login
        self.password_hash = password_hash
        self.is_active = is_active
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

        self._roles: set[Role] = set()
        self._student_profile: StudentProfile | None = None
        self._teacher_profile: TeacherProfile | None = None
        self._parent_profile: ParentProfile | None = None
        self._children: list[User] = []
        self._parents: list[User] = []

    @property
    def roles(self) -> frozenset[Role]:
        return frozenset(self._roles)

    def add_role(self, role: Role) -> None:
        self._roles.add(role)

    def has_role(self, role: Role) -> bool:
        return role in self._roles

    def has_any_role(self, *roles: Role) -> bool:
        return bool(self._roles.intersection(roles))

    @property
    def student_profile(self) -> StudentProfile | None:
        return self._student_profile

    @student_profile.setter
    def student_profile(self, profile: StudentProfile) -> None:
        self._student_profile = profile

    @property
    def teacher_profile(self) -> TeacherProfile | None:
        return self._teacher_profile

    @teacher_profile.setter
    def teacher_profile(self, profile: TeacherProfile) -> None:
        self._teacher_profile = profile

    @property
    def parent_profile(self) -> ParentProfile | None:
        return self._parent_profile

    @parent_profile.setter
    def parent_profile(self, profile: ParentProfile) -> None:
        self._parent_profile = profile

    @property
    def children(self) -> tuple[User, ...]:
        return tuple(self._children)

    def add_child(self, child: User) -> None:
        if child not in self._children:
            self._children.append(child)
        if self not in child._parents:
            child._parents.append(self)

    @property
    def parents(self) -> tuple[User, ...]:
        return tuple(self._parents)

    def __repr__(self) -> str:
        return f"<User id={self.id} login={self.login!r}>"
