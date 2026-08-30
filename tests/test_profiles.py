"""Tests for profiles."""

from datetime import date

from app.infrastructure.database.models import (
    ParentProfileModel,
    StudentProfileModel,
    TeacherProfileModel,
    UserModel,
)


class TestStudentProfile:
    """Tests for StudentProfile."""

    def test_student_profile_creation(self, db):
        """Test student profile creation."""
        user = UserModel(login="student1")
        user.set_password("password")
        db.session.add(user)
        db.session.flush()

        profile = StudentProfileModel(
            user_id=user.id,
            first_name="Ali",
            last_name="Rezaei",
            national_id="1234567890",
            mobile_phone="09121234567",
            birth_date=date(2000, 1, 15),
            gender="MALE",
        )
        db.session.add(profile)
        db.session.commit()

        assert profile.id is not None
        assert profile.user_id == user.id
        assert profile.first_name == "Ali"
        assert profile.last_name == "Rezaei"
        assert profile.national_id == "1234567890"
        assert profile.birth_date == date(2000, 1, 15)
        assert profile.gender == "MALE"

    def test_student_profile_unique_national_id(self, db):
        """Test that national_id is unique."""
        user1 = UserModel(login="student2")
        user1.set_password("pass1")
        user2 = UserModel(login="student3")
        user2.set_password("pass2")
        db.session.add_all([user1, user2])
        db.session.flush()

        profile1 = StudentProfileModel(
            user_id=user1.id,
            first_name="Ali",
            last_name="Rezaei",
            national_id="1234567890",
            mobile_phone="09121234567",
            birth_date=date(2000, 1, 15),
            gender="MALE",
        )
        db.session.add(profile1)
        db.session.commit()

        profile2 = StudentProfileModel(
            user_id=user2.id,
            first_name="Sara",
            last_name="Ahmadi",
            national_id="1234567890",  # Same national_id
            mobile_phone="09121234568",
            birth_date=date(2001, 5, 20),
            gender="FEMALE",
        )
        db.session.add(profile2)

        from sqlalchemy.exc import IntegrityError

        try:
            db.session.commit()
            assert False, "Should have raised IntegrityError"
        except IntegrityError:
            db.session.rollback()

    def test_student_profile_user_relationship(self, db):
        """Test student profile relationship with user."""
        user = UserModel(login="student4")
        user.set_password("password")
        db.session.add(user)
        db.session.flush()

        profile = StudentProfileModel(
            user_id=user.id,
            first_name="Ali",
            last_name="Rezaei",
            national_id="1234567891",
            mobile_phone="09121234567",
            birth_date=date(2000, 1, 15),
            gender="MALE",
        )
        db.session.add(profile)
        db.session.commit()

        assert user.student_profile is not None
        assert user.student_profile.first_name == "Ali"


class TestTeacherProfile:
    """Tests for TeacherProfile."""

    def test_teacher_profile_creation(self, db):
        """Test teacher profile creation."""
        user = UserModel(login="teacher1")
        user.set_password("password")
        db.session.add(user)
        db.session.flush()

        profile = TeacherProfileModel(
            user_id=user.id,
            first_name="Mohammad",
            last_name="Hosseini",
            national_id="9876543210",
            mobile_phone="09129876543",
        )
        db.session.add(profile)
        db.session.commit()

        assert profile.id is not None
        assert profile.first_name == "Mohammad"
        assert profile.last_name == "Hosseini"

    def test_teacher_profile_user_relationship(self, db):
        """Test teacher profile relationship with user."""
        user = UserModel(login="teacher2")
        user.set_password("password")
        db.session.add(user)
        db.session.flush()

        profile = TeacherProfileModel(
            user_id=user.id,
            first_name="Mohammad",
            last_name="Hosseini",
            national_id="9876543211",
            mobile_phone="09129876543",
        )
        db.session.add(profile)
        db.session.commit()

        assert user.teacher_profile is not None
        assert user.teacher_profile.first_name == "Mohammad"


class TestParentProfile:
    """Tests for ParentProfile."""

    def test_parent_profile_creation(self, db):
        """Test parent profile creation."""
        user = UserModel(login="parent1")
        user.set_password("password")
        db.session.add(user)
        db.session.flush()

        profile = ParentProfileModel(
            user_id=user.id,
            first_name="Ahmad",
            last_name="Karimi",
            national_id="5555555555",
            mobile_phone="09125555555",
        )
        db.session.add(profile)
        db.session.commit()

        assert profile.id is not None
        assert profile.first_name == "Ahmad"
        assert profile.last_name == "Karimi"

    def test_parent_student_relationship(self, db):
        """Test parent-student many-to-many relationship."""
        # Create parent user
        parent_user = UserModel(login="parent2")
        parent_user.set_password("password")
        db.session.add(parent_user)
        db.session.flush()

        parent_profile = ParentProfileModel(
            user_id=parent_user.id,
            first_name="Ahmad",
            last_name="Karimi",
            national_id="5555555556",
            mobile_phone="09125555556",
        )
        db.session.add(parent_profile)
        db.session.flush()

        # Create two student users
        student1_user = UserModel(login="student5")
        student1_user.set_password("password")
        db.session.add(student1_user)
        db.session.flush()

        student1_profile = StudentProfileModel(
            user_id=student1_user.id,
            first_name="Ali",
            last_name="Karimi",
            national_id="1111111111",
            mobile_phone="09121111111",
            birth_date=date(2010, 5, 15),
            gender="MALE",
        )
        db.session.add(student1_profile)
        db.session.flush()

        student2_user = UserModel(login="student6")
        student2_user.set_password("password")
        db.session.add(student2_user)
        db.session.flush()

        student2_profile = StudentProfileModel(
            user_id=student2_user.id,
            first_name="Sara",
            last_name="Karimi",
            national_id="2222222222",
            mobile_phone="09122222222",
            birth_date=date(2012, 8, 20),
            gender="FEMALE",
        )
        db.session.add(student2_profile)
        db.session.flush()

        # Create another parent
        parent2_user = UserModel(login="parent3")
        parent2_user.set_password("password")
        db.session.add(parent2_user)
        db.session.flush()

        parent2_profile = ParentProfileModel(
            user_id=parent2_user.id,
            first_name="Zahra",
            last_name="Karimi",
            national_id="6666666666",
            mobile_phone="09126666666",
        )
        db.session.add(parent2_profile)
        db.session.flush()

        # Link parent1 to both students
        parent_profile.children.append(student1_profile)
        parent_profile.children.append(student2_profile)

        # Link parent2 to student1
        parent2_profile.children.append(student1_profile)

        db.session.commit()

        # Verify: Parent A -> Student A, Student B
        assert len(parent_profile.children) == 2
        assert student1_profile in parent_profile.children
        assert student2_profile in parent_profile.children

        # Verify: Student A -> Parent A, Parent B
        assert len(student1_profile.parents) == 2
        assert parent_profile in student1_profile.parents
        assert parent2_profile in student1_profile.parents

        # Verify: Student B -> Parent A only
        assert len(student2_profile.parents) == 1
        assert parent_profile in student2_profile.parents
