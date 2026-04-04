import pytest
from uuid import uuid4
from datetime import datetime
from pydantic import ValidationError
from app.schemas.study_plan import StudyPlanBase, StudyPlanCreate, StudyPlanUpdate, StudyPlanRead
from app.schemas.study_item import StudyItemBase, StudyItemCreate, StudyItemUpdate, StudyItemRead
from app.schemas.courses import CourseBase, CourseRead
from app.schemas.summary import TermSummary, PlanSummary


class TestStudyPlanBase:
    def test_valid(self):
        plan = StudyPlanBase(name="My Plan")
        assert plan.name == "My Plan"
        assert plan.course_count == 0
        assert plan.duration == 0
        assert plan.description is None

    def test_name_required(self):
        with pytest.raises(ValidationError):
            StudyPlanBase()

    def test_all_fields(self):
        plan = StudyPlanBase(name="P", description="D", course_count=5, duration=10)
        assert plan.course_count == 5


class TestStudyPlanCreate:
    def test_valid(self):
        assert StudyPlanCreate(name="New Plan").name == "New Plan"

    def test_requires_name(self):
        with pytest.raises(ValidationError):
            StudyPlanCreate()


class TestStudyPlanUpdate:
    def test_all_optional(self):
        u = StudyPlanUpdate()
        assert u.name is None
        assert u.description is None

    def test_partial(self):
        assert StudyPlanUpdate(name="Updated").name == "Updated"


class TestStudyPlanRead:
    def test_valid(self):
        p = StudyPlanRead(id=uuid4(), user_id=uuid4(), name="P", is_predefined=False)
        assert p.is_predefined is False

    def test_timestamps_optional(self):
        p = StudyPlanRead(id=uuid4(), user_id=uuid4(), name="P", is_predefined=True)
        assert p.created_at is None

    def test_orm_mode(self):
        assert StudyPlanRead.model_config.get("from_attributes") is True


class TestStudyItemBase:
    def test_defaults(self):
        item = StudyItemBase(course_code="CS101", title="Math")
        assert item.status == "planned"
        assert item.position_index == 0
        assert item.term_name == "Unknown"
        assert item.course_category == "Uncategorized"
        assert item.study_plan_id is None
        assert item.course_id is None

    def test_requires_course_code(self):
        with pytest.raises(ValidationError):
            StudyItemBase(title="Math")

    def test_requires_title(self):
        with pytest.raises(ValidationError):
            StudyItemBase(course_code="CS101")

    def test_custom_status(self):
        assert StudyItemBase(course_code="CS101", title="T", status="completed").status == "completed"


class TestStudyItemCreate:
    def test_with_plan_id(self):
        pid = uuid4()
        item = StudyItemCreate(course_code="CS101", title="T", study_plan_id=pid)
        assert item.study_plan_id == pid


class TestStudyItemUpdate:
    def test_all_optional(self):
        u = StudyItemUpdate()
        assert u.course_code is None
        assert u.title is None


class TestStudyItemRead:
    def test_valid(self):
        item = StudyItemRead(item_id=uuid4(), user_id=uuid4(),
                             course_code="CS101", title="T",
                             created_at=datetime.now(), updated_at=datetime.now())
        assert item.item_id is not None

    def test_orm_mode(self):
        assert StudyItemRead.model_config.get("from_attributes") is True


class TestCourseBase:
    def test_valid(self):
        c = CourseBase(course_title="Math 101")
        assert c.course_title == "Math 101"

    def test_requires_title(self):
        with pytest.raises(ValidationError):
            CourseBase()

    def test_optional_fields_none(self):
        c = CourseBase(course_title="CS")
        assert c.course_duration is None
        assert c.course_credit is None


class TestCourseRead:
    def test_valid(self):
        assert CourseRead(course_id=uuid4(), course_title="Algorithms").course_id is not None

    def test_orm_mode(self):
        assert CourseRead.model_config.get("from_attributes") is True


class TestTermSummary:
    def test_valid(self):
        ts = TermSummary(term_id=uuid4(), term_name="T1", course_count=3, total_units=9)
        assert ts.course_count == 3

    def test_requires_fields(self):
        with pytest.raises(ValidationError):
            TermSummary(term_name="T1")


class TestPlanSummary:
    def test_valid(self):
        s = PlanSummary(per_term=[TermSummary(term_id=uuid4(), term_name="T1",
                                              course_count=2, total_units=6)],
                        overall_total_units=6)
        assert s.overall_total_units == 6

    def test_empty_terms(self):
        assert PlanSummary(per_term=[], overall_total_units=0).per_term == []