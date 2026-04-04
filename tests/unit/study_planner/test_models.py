import pytest
from uuid import uuid4, UUID
from app.models.study_plan import StudyPlan
from app.models.study_item import StudyItem
from app.models.courses import Course
from app.models.user import User


class TestStudyPlanModel:
    def test_default_uuid(self):
        plan = StudyPlan(user_id=uuid4(), name="Test")
        assert isinstance(plan.id, UUID)

    def test_two_plans_different_ids(self):
        assert StudyPlan(user_id=uuid4(), name="P1").id != StudyPlan(user_id=uuid4(), name="P2").id

    def test_is_predefined_defaults_false(self):
        assert StudyPlan(user_id=uuid4(), name="T").is_predefined is False

    def test_course_count_defaults_zero(self):
        assert StudyPlan(user_id=uuid4(), name="T").course_count == 0

    def test_duration_defaults_zero(self):
        assert StudyPlan(user_id=uuid4(), name="T").duration == 0

    def test_description_optional(self):
        assert StudyPlan(user_id=uuid4(), name="T").description is None

    def test_tablename(self):
        assert StudyPlan.__tablename__ == "study_plans"

    def test_schema(self):
        assert StudyPlan.__table_args__["schema"] == "stud_hub_schema"


class TestStudyItemModel:
    def test_default_uuid(self):
        item = StudyItem(user_id=uuid4(), course_code="CS101", title="T")
        assert isinstance(item.item_id, UUID)

    def test_two_items_different_ids(self):
        a = StudyItem(user_id=uuid4(), course_code="CS101", title="A")
        b = StudyItem(user_id=uuid4(), course_code="CS102", title="B")
        assert a.item_id != b.item_id

    def test_status_defaults_planned(self):
        assert StudyItem(user_id=uuid4(), course_code="CS101", title="T").status == "planned"

    def test_position_index_defaults_zero(self):
        assert StudyItem(user_id=uuid4(), course_code="CS101", title="T").position_index == 0

    def test_term_name_default(self):
        assert StudyItem(user_id=uuid4(), course_code="CS101", title="T").term_name == "Unknown"

    def test_course_category_default(self):
        assert StudyItem(user_id=uuid4(), course_code="CS101", title="T").course_category == "Uncategorized"

    def test_study_plan_id_optional(self):
        assert StudyItem(user_id=uuid4(), course_code="CS101", title="T").study_plan_id is None

    def test_tablename(self):
        assert StudyItem.__tablename__ == "study_items"

    def test_schema(self):
        assert StudyItem.__table_args__["schema"] == "stud_hub_schema"


class TestCourseModel:
    def test_tablename(self):
        assert Course.__tablename__ == "courses"

    def test_schema(self):
        assert Course.__table_args__["schema"] == "stud_hub_schema"


class TestUserModel:
    def test_tablename(self):
        assert User.__tablename__ == "users"

    def test_schema(self):
        assert User.__table_args__["schema"] == "stud_hub_schema"