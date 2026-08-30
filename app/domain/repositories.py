from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.enrollment import Enrollment
from app.domain.profiles import ParentProfile, StudentProfile, TeacherProfile
from app.domain.role import Role
from app.domain.user import User


class UserRepository(ABC):
    """Abstract repository for User persistence."""

    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None: ...

    @abstractmethod
    def get_by_login(self, login: str) -> User | None: ...

    @abstractmethod
    def create(self, user: User) -> User: ...

    @abstractmethod
    def update(self, user: User) -> User: ...

    @abstractmethod
    def get_user_roles(self, user_id: int) -> set[Role]: ...

    @abstractmethod
    def add_role(self, user_id: int, role: Role) -> None: ...

    @abstractmethod
    def remove_role(self, user_id: int, role: Role) -> None: ...


class StudentProfileRepository(ABC):
    """Abstract repository for StudentProfile persistence."""

    @abstractmethod
    def get_by_user_id(self, user_id: int) -> StudentProfile | None: ...

    @abstractmethod
    def get_by_national_id(self, national_id: str) -> StudentProfile | None: ...

    @abstractmethod
    def create(self, profile: StudentProfile) -> StudentProfile: ...


class TeacherProfileRepository(ABC):
    """Abstract repository for TeacherProfile persistence."""

    @abstractmethod
    def get_by_user_id(self, user_id: int) -> TeacherProfile | None: ...

    @abstractmethod
    def create(self, profile: TeacherProfile) -> TeacherProfile: ...


class ParentProfileRepository(ABC):
    """Abstract repository for ParentProfile persistence."""

    @abstractmethod
    def get_by_user_id(self, user_id: int) -> ParentProfile | None: ...

    @abstractmethod
    def create(self, profile: ParentProfile) -> ParentProfile: ...

    @abstractmethod
    def link_child(self, parent_id: int, child_id: int) -> None: ...

    @abstractmethod
    def get_children(self, parent_id: int) -> list[User]: ...

    @abstractmethod
    def get_parents(self, child_id: int) -> list[User]: ...


class EnrollmentRepository(ABC):
    """Abstract repository for Enrollment persistence."""

    @abstractmethod
    def get_by_id(self, enrollment_id: int) -> Enrollment | None: ...

    @abstractmethod
    def get_by_student_and_class(
        self, student_user_id: int, class_id: int
    ) -> Enrollment | None: ...

    @abstractmethod
    def get_active_enrollment(
        self, student_user_id: int, class_id: int
    ) -> Enrollment | None: ...

    @abstractmethod
    def create(self, enrollment: Enrollment) -> Enrollment: ...

    @abstractmethod
    def update(self, enrollment: Enrollment) -> Enrollment: ...

    @abstractmethod
    def list_by_student(self, student_user_id: int) -> list[Enrollment]: ...

    @abstractmethod
    def list_by_class(self, class_id: int) -> list[Enrollment]: ...

    @abstractmethod
    def list_pending_by_class(self, class_id: int) -> list[Enrollment]: ...

    @abstractmethod
    def count_approved_by_class(self, class_id: int) -> int: ...
