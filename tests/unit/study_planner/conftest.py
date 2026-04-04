import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../study_planner"))

from study_planner.app.main import app
from study_planner.app.api.deps import DBSessionDep, CurrentUserDep
from study_planner.app.core.security import CurrentUser

ADMIN_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_USER_ID = uuid4()
TEST_PLAN_ID = uuid4()
TEST_ITEM_ID = uuid4()
TEST_COURSE_ID = uuid4()


def make_mock_user(user_id=None):
    user = MagicMock(spec=CurrentUser)
    user.id = user_id or TEST_USER_ID
    return user


def make_mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.execute = AsyncMock()
    return db


def make_mock_plan(plan_id=None, user_id=None, is_predefined=False,
                   name="Test Plan", description="Test Desc",
                   course_count=0, duration=0, study_items=None):
    plan = MagicMock()
    plan.id = plan_id or TEST_PLAN_ID
    plan.user_id = user_id or TEST_USER_ID
    plan.is_predefined = is_predefined
    plan.name = name
    plan.description = description
    plan.course_count = course_count
    plan.duration = duration
    plan.created_at = datetime(2024, 1, 1)
    plan.updated_at = datetime(2024, 1, 1)
    plan.study_items = study_items or []
    return plan


def make_mock_item(item_id=None, user_id=None, plan_id=None,
                   course_code="CS101", title="Test Item", status="planned",
                   position_index=0, term_name="Term 1", course_category="CS"):
    item = MagicMock()
    item.item_id = item_id or TEST_ITEM_ID
    item.user_id = user_id or TEST_USER_ID
    item.study_plan_id = plan_id or TEST_PLAN_ID
    item.course_code = course_code
    item.title = title
    item.status = status
    item.position_index = position_index
    item.term_name = term_name
    item.course_category = course_category
    item.course_id = TEST_COURSE_ID
    item.created_at = datetime(2024, 1, 1)
    item.updated_at = datetime(2024, 1, 1)
    return item


def make_mock_course(course_id=None, course_title="Test Course",
                     course_code="CS101", course_category="CS",
                     course_duration=3, course_credit=4):
    course = MagicMock()
    course.course_id = course_id or TEST_COURSE_ID
    course.course_title = course_title
    course.course_code = course_code
    course.course_category = course_category
    course.course_duration = course_duration
    course.course_credit = course_credit
    course.course_desc = "Test description"
    course.created_at = datetime(2024, 1, 1)
    return course


@pytest.fixture
def mock_db(): return make_mock_db()

@pytest.fixture
def mock_user(): return make_mock_user()

@pytest.fixture
def mock_plan(): return make_mock_plan()

@pytest.fixture
def mock_item(): return make_mock_item()

@pytest.fixture
def mock_course(): return make_mock_course()

@pytest.fixture
def client(mock_db, mock_user):
    app.dependency_overrides[DBSessionDep] = lambda: mock_db
    app.dependency_overrides[CurrentUserDep] = lambda: mock_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()