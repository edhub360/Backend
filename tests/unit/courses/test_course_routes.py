# tests/unit/courses/test_routes_courses.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_course_row(**kwargs):
    defaults = dict(
        course_id="course-uuid-1",
        course_title="Python Basics",
        course_desc="A" * 300,
        course_duration=120,
        course_complexity="beginner",
        course_owner="instructor-1",
        course_url="https://cdn.example.com/python",
        course_redirect_url="https://example.com/python",
        course_image_url="https://cdn.example.com/img.png",
        course_credit=3,
        created_at=datetime(2024, 1, 15, 10, 30, 0),
    )
    defaults.update(kwargs)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def make_app():
    from courses.app.routes.courses import router
    from courses.app.db import get_db

    app = FastAPI()
    mock_db = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    app.include_router(router, prefix="/courses")
    return app, mock_db


# ─────────────────────────────────────────────
# List courses  GET /courses/
# ─────────────────────────────────────────────

class TestListCoursesEndpoint:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_list = AsyncMock(return_value=(0, []))
        self.mock_validate = MagicMock()

        with patch("courses.app.routes.courses.list_courses", self.mock_list), \
             patch("courses.app.routes.courses.validate_pagination", self.mock_validate):
            app, self.mock_db = make_app()
            self.client = TestClient(app, raise_server_exceptions=False)
            yield

    def test_returns_200_with_courses(self):
        self.mock_list.return_value = (1, [make_course_row()])
        response = self.client.get("/courses/")
        assert response.status_code == 200

    def test_response_shape(self):
        self.mock_list.return_value = (1, [make_course_row()])
        data = self.client.get("/courses/").json()
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "items" in data

    def test_short_description_truncated_to_200(self):
        self.mock_list.return_value = (1, [make_course_row(course_desc="X" * 300)])
        data = self.client.get("/courses/").json()
        assert len(data["items"][0]["short_description"]) == 200

    def test_none_course_desc_becomes_empty_string(self):
        self.mock_list.return_value = (1, [make_course_row(course_desc=None)])
        data = self.client.get("/courses/").json()
        assert data["items"][0]["short_description"] == ""

    def test_last_item_rotated_to_first(self):
        courses = [make_course_row(course_id=f"id-{i}", course_title=f"Course {i}") for i in range(3)]
        self.mock_list.return_value = (3, courses)
        data = self.client.get("/courses/").json()
        assert data["items"][0]["course_id"] == "id-2"
        assert data["items"][1]["course_id"] == "id-0"
        assert data["items"][2]["course_id"] == "id-1"

    def test_single_item_rotation_is_stable(self):
        self.mock_list.return_value = (1, [make_course_row(course_id="only-one")])
        data = self.client.get("/courses/").json()
        assert data["items"][0]["course_id"] == "only-one"

    def test_empty_items_list(self):
        self.mock_list.return_value = (0, [])
        data = self.client.get("/courses/").json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_pagination_meta_reflects_query_params(self):
        self.mock_list.return_value = (50, [])
        data = self.client.get("/courses/?page=3&limit=5").json()
        assert data["page"] == 3
        assert data["limit"] == 5
        assert data["total"] == 50

    def test_search_query_passed_to_crud(self):
        self.mock_list.return_value = (0, [])
        self.client.get("/courses/?q=python")
        args = self.mock_list.call_args[0]
        assert args[1] == "python"

    def test_complexity_filter_passed_to_crud(self):
        self.mock_list.return_value = (0, [])
        self.client.get("/courses/?complexity=advanced")
        args = self.mock_list.call_args[0]
        assert args[4] == "advanced"

    def test_duration_filters_passed_to_crud(self):
        self.mock_list.return_value = (0, [])
        self.client.get("/courses/?min_duration=30&max_duration=120")
        args = self.mock_list.call_args[0]
        assert args[5] == 30
        assert args[6] == 120

    def test_invalid_pagination_raises_400(self):
        self.mock_validate.side_effect = ValueError("limit exceeds max")
        response = self.client.get("/courses/")
        assert response.status_code == 400
        assert "limit exceeds max" in response.json()["detail"]

    def test_page_less_than_1_returns_422(self):
        response = self.client.get("/courses/?page=0")
        assert response.status_code == 422

    def test_limit_less_than_1_returns_422(self):
        response = self.client.get("/courses/?limit=0")
        assert response.status_code == 422

    def test_min_duration_negative_returns_422(self):
        response = self.client.get("/courses/?min_duration=-1")
        assert response.status_code == 422


# ─────────────────────────────────────────────
# Get course  GET /courses/{course_id}
# ─────────────────────────────────────────────

class TestGetCourseEndpoint:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_get = AsyncMock(return_value=None)

        with patch("courses.app.routes.courses.get_course", self.mock_get):
            app, self.mock_db = make_app()
            self.client = TestClient(app, raise_server_exceptions=False)
            yield

    def test_returns_200_when_found(self):
        self.mock_get.return_value = make_course_row()
        response = self.client.get("/courses/course-uuid-1")
        assert response.status_code == 200

    def test_returns_404_when_not_found(self):
        self.mock_get.return_value = None
        response = self.client.get("/courses/nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "Course not found"

    def test_response_contains_all_fields(self):
        self.mock_get.return_value = make_course_row()
        data = self.client.get("/courses/course-uuid-1").json()
        for field in [
            "course_id", "course_title", "course_desc", "course_duration",
            "course_complexity", "course_owner", "course_url",
            "course_redirect_url", "course_image_url", "course_credit", "created_at"
        ]:
            assert field in data, f"Missing field: {field}"

    def test_created_at_is_isoformat_string(self):
        self.mock_get.return_value = make_course_row(created_at=datetime(2024, 6, 1, 12, 0, 0))
        data = self.client.get("/courses/course-uuid-1").json()
        assert data["created_at"] == "2024-06-01T12:00:00"

    def test_course_id_passed_to_crud(self):
        self.mock_get.return_value = None
        self.client.get("/courses/my-specific-id")
        self.mock_get.assert_called_once()
        assert self.mock_get.call_args[0][1] == "my-specific-id"

    def test_full_desc_returned_not_truncated(self):
        long_desc = "D" * 500
        self.mock_get.return_value = make_course_row(course_desc=long_desc)
        data = self.client.get("/courses/course-uuid-1").json()
        assert len(data["course_desc"]) == 500

    def test_course_credit_value(self):
        self.mock_get.return_value = make_course_row(course_credit=5)
        data = self.client.get("/courses/course-uuid-1").json()
        assert data["course_credit"] == 5


# ─────────────────────────────────────────────
# Featured courses  GET /courses/featured
# NOTE: /featured must be registered BEFORE /{course_id} in the router
# ─────────────────────────────────────────────

class TestFeaturedCoursesEndpoint:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_list = AsyncMock(return_value=(0, []))

        with patch("courses.app.routes.courses.list_courses", self.mock_list):
            app, self.mock_db = make_app()
            self.client = TestClient(app, raise_server_exceptions=False)
            yield

    def test_returns_200(self):
        self.mock_list.return_value = (3, [make_course_row() for _ in range(3)])
        response = self.client.get("/courses/featured")
        assert response.status_code == 200

    def test_page_is_always_1(self):
        self.mock_list.return_value = (2, [make_course_row(), make_course_row()])
        data = self.client.get("/courses/featured").json()
        assert data["page"] == 1

    def test_crud_called_with_page_1(self):
        self.mock_list.return_value = (0, [])
        self.client.get("/courses/featured")
        args = self.mock_list.call_args[0]
        assert args[2] == 1      # page
        assert args[1] is None   # q=None

    def test_custom_limit_respected(self):
        self.mock_list.return_value = (0, [])
        self.client.get("/courses/featured?limit=3")
        args = self.mock_list.call_args[0]
        assert args[3] == 3      # limit

    def test_no_item_rotation_applied(self):
        courses = [make_course_row(course_id=f"f-{i}") for i in range(3)]
        self.mock_list.return_value = (3, courses)
        data = self.client.get("/courses/featured").json()
        assert data["items"][0]["course_id"] == "f-0"

    def test_short_description_truncated(self):
        self.mock_list.return_value = (1, [make_course_row(course_desc="Y" * 300)])
        data = self.client.get("/courses/featured").json()
        assert len(data["items"][0]["short_description"]) == 200

    def test_none_desc_becomes_empty_string(self):
        self.mock_list.return_value = (1, [make_course_row(course_desc=None)])
        data = self.client.get("/courses/featured").json()
        assert data["items"][0]["short_description"] == ""

    def test_limit_below_1_returns_422(self):
        response = self.client.get("/courses/featured?limit=0")
        assert response.status_code == 422