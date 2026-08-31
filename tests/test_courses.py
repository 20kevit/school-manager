"""Tests for Course and Syllabus services."""

import pytest

from app.application.academy.course_service import (
    CourseError,
    add_syllabus_item,
    create_course,
    delete_course,
    delete_syllabus_item,
    get_course,
    get_syllabus_items,
    list_courses,
    update_course,
    update_syllabus_item,
)


class TestCourseCreation:
    """Tests for course creation."""

    def test_create_course_basic(self, db):
        course = create_course(title="Python Beginner", num_sessions=10)
        assert course.id is not None
        assert course.title == "Python Beginner"
        assert course.num_sessions == 10

    def test_create_course_with_all_fields(self, db):
        course = create_course(
            title="Advanced Python",
            description="Advanced Python programming",
            num_sessions=12,
            min_age=16,
            max_age=25,
            prerequisites="Python basics",
        )
        assert course.title == "Advanced Python"
        assert course.description == "Advanced Python programming"
        assert course.min_age == 16
        assert course.max_age == 25
        assert course.prerequisites == "Python basics"

    def test_create_course_empty_title_fails(self, db):
        with pytest.raises(CourseError, match="title is required"):
            create_course(title="")

    def test_create_course_whitespace_title_fails(self, db):
        with pytest.raises(CourseError, match="title is required"):
            create_course(title="   ")

    def test_create_course_zero_sessions_fails(self, db):
        with pytest.raises(CourseError, match="at least 1"):
            create_course(title="Test", num_sessions=0)

    def test_create_course_negative_sessions_fails(self, db):
        with pytest.raises(CourseError, match="at least 1"):
            create_course(title="Test", num_sessions=-1)

    def test_create_course_min_age_greater_than_max_fails(self, db):
        with pytest.raises(CourseError, match="cannot be greater"):
            create_course(title="Test", min_age=20, max_age=10)

    def test_create_course_strips_whitespace(self, db):
        course = create_course(title="  Python  ")
        assert course.title == "Python"


class TestCourseUpdate:
    """Tests for course updates."""

    def test_update_course_title(self, db):
        course = create_course(title="Old Title")
        update_course(course, title="New Title")
        assert course.title == "New Title"

    def test_update_course_description(self, db):
        course = create_course(title="Test")
        update_course(course, description="New description")
        assert course.description == "New description"

    def test_update_course_num_sessions(self, db):
        course = create_course(title="Test", num_sessions=5)
        update_course(course, num_sessions=10)
        assert course.num_sessions == 10

    def test_update_course_empty_title_fails(self, db):
        course = create_course(title="Test")
        with pytest.raises(CourseError, match="cannot be empty"):
            update_course(course, title="")

    def test_update_course_zero_sessions_fails(self, db):
        course = create_course(title="Test", num_sessions=5)
        with pytest.raises(CourseError, match="at least 1"):
            update_course(course, num_sessions=0)


class TestCourseQuery:
    """Tests for course queries."""

    def test_get_course(self, db):
        course = create_course(title="Test")
        fetched = get_course(course.id)
        assert fetched is not None
        assert fetched.title == "Test"

    def test_get_nonexistent_course(self, db):
        assert get_course(9999) is None

    def test_list_courses_ordered(self, db):
        create_course(title="Zebra")
        create_course(title="Alpha")
        create_course(title="Middle")
        courses = list_courses()
        titles = [c.title for c in courses]
        assert titles == ["Alpha", "Middle", "Zebra"]

    def test_delete_course(self, db):
        course = create_course(title="To Delete")
        delete_course(course)
        assert get_course(course.id) is None


class TestSyllabus:
    """Tests for syllabus item management."""

    def test_add_syllabus_item(self, db):
        course = create_course(title="Test", num_sessions=3)
        item = add_syllabus_item(course, order=1, title="Introduction")
        assert item.id is not None
        assert item.order == 1
        assert item.title == "Introduction"

    def test_add_syllabus_item_with_all_fields(self, db):
        course = create_course(title="Test")
        item = add_syllabus_item(
            course,
            order=1,
            title="Session 1",
            description="Learn basics",
            homework="Exercise 1",
            assessment="Quiz 1",
        )
        assert item.description == "Learn basics"
        assert item.homework == "Exercise 1"
        assert item.assessment == "Quiz 1"

    def test_add_syllabus_duplicate_order_fails(self, db):
        course = create_course(title="Test")
        add_syllabus_item(course, order=1, title="First")
        with pytest.raises(CourseError, match="already exists"):
            add_syllabus_item(course, order=1, title="Second")

    def test_add_syllabus_empty_title_fails(self, db):
        course = create_course(title="Test")
        with pytest.raises(CourseError, match="title is required"):
            add_syllabus_item(course, order=1, title="")

    def test_add_syllabus_order_zero_fails(self, db):
        course = create_course(title="Test")
        with pytest.raises(CourseError, match="at least 1"):
            add_syllabus_item(course, order=0, title="Test")

    def test_get_syllabus_items_ordered(self, db):
        course = create_course(title="Test")
        add_syllabus_item(course, order=3, title="Third")
        add_syllabus_item(course, order=1, title="First")
        add_syllabus_item(course, order=2, title="Second")
        items = get_syllabus_items(course.id)
        assert [i.order for i in items] == [1, 2, 3]

    def test_update_syllabus_item(self, db):
        course = create_course(title="Test")
        item = add_syllabus_item(course, order=1, title="Old Title")
        update_syllabus_item(item, title="New Title")
        assert item.title == "New Title"

    def test_update_syllabus_order(self, db):
        course = create_course(title="Test")
        item1 = add_syllabus_item(course, order=1, title="First")
        item2 = add_syllabus_item(course, order=2, title="Second")
        add_syllabus_item(course, order=3, title="Third")
        update_syllabus_item(item1, order=4)
        update_syllabus_item(item2, order=1)
        update_syllabus_item(item1, order=2)
        items = get_syllabus_items(course.id)
        assert items[0].title == "Second"
        assert items[1].title == "First"
        assert items[2].title == "Third"

    def test_delete_syllabus_item(self, db):
        course = create_course(title="Test")
        item = add_syllabus_item(course, order=1, title="To Delete")
        delete_syllabus_item(item)
        items = get_syllabus_items(course.id)
        assert len(items) == 0


class TestAgeRestrictions:
    """Tests for course age restriction semantics."""

    def test_no_restrictions(self, db):
        course = create_course(title="Open Course")
        assert course.min_age is None
        assert course.max_age is None

    def test_only_min_age(self, db):
        course = create_course(title="Adults Only", min_age=18)
        assert course.min_age == 18
        assert course.max_age is None

    def test_only_max_age(self, db):
        course = create_course(title="Kids Only", max_age=12)
        assert course.min_age is None
        assert course.max_age == 12

    def test_both_restrictions(self, db):
        course = create_course(title="Teens", min_age=13, max_age=17)
        assert course.min_age == 13
        assert course.max_age == 17

    def test_negative_min_age_fails(self, db):
        with pytest.raises(CourseError):
            create_course(title="Bad", min_age=-1)

    def test_negative_max_age_fails(self, db):
        with pytest.raises(CourseError):
            create_course(title="Bad", max_age=-1)

    def test_min_greater_than_max_fails(self, db):
        with pytest.raises(CourseError):
            create_course(title="Bad", min_age=20, max_age=10)

    def test_update_age_restrictions(self, db):
        course = create_course(title="Test", min_age=10, max_age=20)
        update_course(course, min_age=15)
        assert course.min_age == 15
        assert course.max_age == 20

    def test_clear_min_age(self, db):
        course = create_course(title="Test", min_age=10, max_age=20)
        update_course(course, min_age=None)
        assert course.min_age is None
        assert course.max_age == 20


class TestSyllabusAutoNumbering:
    """Tests for syllabus auto-numbering helper."""

    def test_get_next_syllabus_order(self, db):
        from app.application.academy.course_service import get_next_syllabus_order

        course = create_course(title="Test")
        assert get_next_syllabus_order(course.id) == 1
        add_syllabus_item(course, order=1, title="First")
        assert get_next_syllabus_order(course.id) == 2
        add_syllabus_item(course, order=2, title="Second")
        assert get_next_syllabus_order(course.id) == 3
