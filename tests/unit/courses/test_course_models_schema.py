# tests/unit/courses/test_models_and_schemas.py

import pytest
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock
import os


# ══════════════════════════════════════════════
# models.py
# ══════════════════════════════════════════════
from courses.app.models import Course

class TestCourseModel:

    @pytest.fixture(autouse=True)
    def import_model(self):
        import sys
        # Pop both modules so SQLAlchemy's MetaData starts fresh each test.
        # This prevents "Table already defined" errors across the test class.
        sys.modules.pop("courses.app.models", None)
        sys.modules.pop("courses.app.db", None)
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://u:p@localhost/db"}), \
             patch("sqlalchemy.ext.asyncio.create_async_engine"), \
             patch("sqlalchemy.ext.asyncio.async_sessionmaker"):
            self.Course = Course

    def test_tablename_is_courses(self):
        assert self.Course.__tablename__ == "courses"

    def test_schema_is_stud_hub_schema(self):
        # __table_args__ can be a dict OR a tuple ending with a dict.
        # Handle both forms safely.
        table_args = self.Course.__table_args__
        if isinstance(table_args, dict):
            schema = table_args.get("schema")
        else:
            # tuple form: (..., {"schema": "..."})
            schema = table_args[-1].get("schema")
        assert schema == "stud_hub_schema"

    def test_course_id_is_primary_key(self):
        col = self.Course.__table__.c["course_id"]
        assert col.primary_key is True

    def test_course_id_is_unique(self):
        col = self.Course.__table__.c["course_id"]
        # A primary key column is implicitly unique in the DB, but SQLAlchemy
        # does NOT set col.unique=True on PK columns — check both.
        assert col.primary_key is True or col.unique is True

    def test_course_id_is_not_nullable(self):
        col = self.Course.__table__.c["course_id"]
        assert col.nullable is False

    def test_course_id_default_is_uuid4(self):
        col = self.Course.__table__.c["course_id"]
        # The column default callable should be uuid.uuid4
        assert col.default.arg is uuid.uuid4

    def test_course_title_is_not_nullable(self):
        col = self.Course.__table__.c["course_title"]
        assert col.nullable is False

    def test_created_at_is_not_nullable(self):
        col = self.Course.__table__.c["created_at"]
        assert col.nullable is False

    def test_course_desc_is_nullable(self):
        col = self.Course.__table__.c["course_desc"]
        assert col.nullable is True

    def test_course_duration_is_nullable(self):
        col = self.Course.__table__.c["course_duration"]
        assert col.nullable is True

    def test_course_complexity_is_nullable(self):
        col = self.Course.__table__.c["course_complexity"]
        assert col.nullable is True

    def test_course_owner_is_nullable(self):
        col = self.Course.__table__.c["course_owner"]
        assert col.nullable is True

    def test_course_url_is_nullable(self):
        col = self.Course.__table__.c["course_url"]
        assert col.nullable is True

    def test_course_redirect_url_is_nullable(self):
        col = self.Course.__table__.c["course_redirect_url"]
        assert col.nullable is True

    def test_course_image_url_is_nullable(self):
        col = self.Course.__table__.c["course_image_url"]
        assert col.nullable is True

    def test_course_credit_is_nullable(self):
        col = self.Course.__table__.c["course_credit"]
        assert col.nullable is True

    def test_expected_columns_present(self):
        cols = set(self.Course.__table__.c.keys())
        expected = {
            "course_id", "course_title", "course_desc", "course_duration",
            "course_complexity", "course_owner", "course_url",
            "course_redirect_url", "course_image_url", "course_credit", "created_at"
        }
        assert expected == cols

    def test_instantiation_with_required_fields(self):
        course = self.Course(
            course_title="Test Course",
            created_at=datetime(2024, 1, 1),
        )
        assert course.course_title == "Test Course"

    def test_instantiation_with_all_fields(self):
        uid = uuid.uuid4()
        course = self.Course(
            course_id=uid,
            course_title="Full Course",
            course_desc="Description here",
            course_duration=90,
            course_complexity="intermediate",
            course_owner="owner-1",
            course_url="https://cdn.example.com",
            course_redirect_url="https://example.com",
            course_image_url="https://cdn.example.com/img.png",
            course_credit=4,
            created_at=datetime(2024, 6, 1),
        )
        assert course.course_id == uid
        assert course.course_credit == 4
        assert course.course_complexity == "intermediate"

    def test_model_inherits_from_base(self):
        import sys
        # db module was already imported in import_model, fetch it from sys.modules
        # so we don't trigger a second import with a fresh MetaData.
        db_module = sys.modules.get("courses.app.db")
        assert db_module is not None, "courses.app.db was not imported by import_model fixture"
        Base = db_module.Base
        assert issubclass(self.Course, Base)


# ══════════════════════════════════════════════
# schemas.py
# ══════════════════════════════════════════════


class TestCoursePreviewSchema:

    @pytest.fixture(autouse=True)
    def import_schema(self):
        from courses.app.schemas import CoursePreview
        self.CoursePreview = CoursePreview

    def _valid(self, **kwargs):
        defaults = dict(
            course_id=uuid.uuid4(),
            course_title="Python Basics",
            short_description="Short desc",
            course_duration=60,
            course_complexity="beginner",
            course_image_url="https://cdn.example.com/img.png",
            course_redirect_url="https://example.com/py",
            course_credit=3,
        )
        defaults.update(kwargs)
        return self.CoursePreview(**defaults)

    def test_valid_construction(self):
        preview = self._valid()
        assert preview.course_title == "Python Basics"

    def test_course_id_is_uuid(self):
        uid = uuid.uuid4()
        preview = self._valid(course_id=uid)
        assert preview.course_id == uid

    def test_optional_fields_can_be_none(self):
        preview = self._valid(
            short_description=None,
            course_duration=None,
            course_complexity=None,
            course_image_url=None,
            course_redirect_url=None,
            course_credit=None,
        )
        assert preview.short_description is None
        assert preview.course_duration is None
        assert preview.course_credit is None

    def test_course_title_required(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self.CoursePreview(course_id=uuid.uuid4())

    def test_course_id_required(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self.CoursePreview(course_title="No ID")

    def test_invalid_course_id_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self._valid(course_id="not-a-uuid")

    def test_serializes_to_dict(self):
        preview = self._valid()
        data = preview.model_dump()
        assert "course_id" in data
        assert "course_title" in data
        assert "short_description" in data

    def test_all_expected_fields_in_schema(self):
        fields = set(self.CoursePreview.model_fields.keys())
        expected = {
            "course_id", "course_title", "short_description",
            "course_duration", "course_complexity", "course_image_url",
            "course_redirect_url", "course_credit"
        }
        assert expected == fields


class TestCourseDetailSchema:

    @pytest.fixture(autouse=True)
    def import_schema(self):
        from courses.app.schemas import CourseDetail
        self.CourseDetail = CourseDetail

    def _valid(self, **kwargs):
        defaults = dict(
            course_id=uuid.uuid4(),
            course_title="Advanced Django",
            course_desc="Full description here",
            course_duration=120,
            course_complexity="advanced",
            course_owner="instructor-1",
            course_url="https://cdn.example.com/django",
            course_redirect_url="https://example.com/django",
            course_image_url="https://cdn.example.com/img.png",
            course_credit=5,
            created_at="2024-01-15T10:30:00",
        )
        defaults.update(kwargs)
        return self.CourseDetail(**defaults)

    def test_valid_construction(self):
        detail = self._valid()
        assert detail.course_title == "Advanced Django"

    def test_created_at_is_string(self):
        detail = self._valid(created_at="2024-06-01T12:00:00")
        assert isinstance(detail.created_at, str)
        assert detail.created_at == "2024-06-01T12:00:00"

    def test_course_id_required(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self.CourseDetail(course_title="No ID", created_at="2024-01-01T00:00:00")

    def test_course_title_required(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self.CourseDetail(course_id=uuid.uuid4(), created_at="2024-01-01T00:00:00")

    def test_created_at_required(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self.CourseDetail(course_id=uuid.uuid4(), course_title="No date")

    def test_optional_fields_can_be_none(self):
        detail = self._valid(
            course_desc=None,
            course_duration=None,
            course_complexity=None,
            course_owner=None,
            course_url=None,
            course_redirect_url=None,
            course_image_url=None,
            course_credit=None,
        )
        assert detail.course_desc is None
        assert detail.course_owner is None

    def test_all_expected_fields_in_schema(self):
        fields = set(self.CourseDetail.model_fields.keys())
        expected = {
            "course_id", "course_title", "course_desc", "course_duration",
            "course_complexity", "course_owner", "course_url",
            "course_redirect_url", "course_image_url", "course_credit", "created_at"
        }
        assert expected == fields

    def test_serializes_to_dict(self):
        detail = self._valid()
        data = detail.model_dump()
        assert "created_at" in data
        assert "course_owner" in data


class TestPaginatedCoursesSchema:

    @pytest.fixture(autouse=True)
    def import_schema(self):
        from courses.app.schemas import PaginatedCourses, CoursePreview
        self.PaginatedCourses = PaginatedCourses
        self.CoursePreview = CoursePreview

    def _preview(self, **kwargs):
        defaults = dict(
            course_id=uuid.uuid4(),
            course_title="Course",
            short_description="desc",
            course_duration=30,
            course_complexity="beginner",
            course_image_url=None,
            course_redirect_url=None,
            course_credit=1,
        )
        defaults.update(kwargs)
        return self.CoursePreview(**defaults)

    def test_valid_construction(self):
        paginated = self.PaginatedCourses(total=10, page=1, limit=10, items=[])
        assert paginated.total == 10

    def test_items_is_list_of_course_preview(self):
        items = [self._preview()]
        paginated = self.PaginatedCourses(total=1, page=1, limit=10, items=items)
        assert len(paginated.items) == 1
        assert isinstance(paginated.items[0], self.CoursePreview)

    def test_empty_items_list(self):
        paginated = self.PaginatedCourses(total=0, page=1, limit=10, items=[])
        assert paginated.items == []

    def test_total_required(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self.PaginatedCourses(page=1, limit=10, items=[])

    def test_page_required(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self.PaginatedCourses(total=0, limit=10, items=[])

    def test_limit_required(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self.PaginatedCourses(total=0, page=1, items=[])

    def test_items_required(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self.PaginatedCourses(total=0, page=1, limit=10)

    def test_multiple_items(self):
        items = [self._preview(course_id=uuid.uuid4()) for _ in range(5)]
        paginated = self.PaginatedCourses(total=5, page=1, limit=10, items=items)
        assert len(paginated.items) == 5

    def test_page_and_limit_values_preserved(self):
        paginated = self.PaginatedCourses(total=100, page=4, limit=25, items=[])
        assert paginated.page == 4
        assert paginated.limit == 25

    def test_serializes_to_dict(self):
        paginated = self.PaginatedCourses(total=1, page=1, limit=10, items=[self._preview()])
        data = paginated.model_dump()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_items_type_rejects_non_preview(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self.PaginatedCourses(total=1, page=1, limit=10, items=["not-a-preview"])