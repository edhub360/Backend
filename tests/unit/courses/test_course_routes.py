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
    # Set attributes explicitly so MagicMock doesn't auto-create wrong types.
    # Accessing mock.course_desc on a plain MagicMock() returns another MagicMock,
    # not None or a string — which breaks len() checks and None comparisons.
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def make_app():
    """Build a fresh FastAPI app with the get_db dependency properly overridden."""
    from courses.app.routes.courses import router
    from courses.app.db import get_db

    app = FastAPI()

    # FIXED: get_db is an async generator (yields a session), so the override
    # must also be an async generator — not a plain lambda returning AsyncMock.
    # A lambda returning AsyncMock bypasses the yield, causing 'coroutine has
    # no attribute ...' errors inside the route when it awaits the session.
    mock_db = AsyncMock()

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
        self.app, self.mock_db = make_app()
        self.client = TestClient(self.app, raise_server_exceptions=False)

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    @patch("courses.app.routes.courses.validate_pagination")
    def test_returns_200_with_courses(self, mock_validate, mock_list):
        course = make_course_row()
        mock_list.return_value = (1, [course])
        response = self.client.get("/courses/")
        assert response.status_code == 200

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    @patch("courses.app.routes.courses.validate_pagination")
    def test_response_shape(self, mock_validate, mock_list):
        course = make_course_row()
        mock_list.return_value = (1, [course])
        data = self.client.get("/courses/").json()
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "items" in data

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    @patch("courses.app.routes.courses.validate_pagination")
    def test_short_description_truncated_to_200(self, mock_validate, mock_list):
        course = make_course_row(course_desc="X" * 300)
        mock_list.return_value = (1, [course])
        data = self.client.get("/courses/").json()
        assert len(data["items"][0]["short_description"]) == 200

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    @patch("courses.app.routes.courses.validate_pagination")
    def test_none_course_desc_becomes_empty_string(self, mock_validate, mock_list):
        course = make_course_row(course_desc=None)
        mock_list.return_value = (1, [course])
        data = self.client.get("/courses/").json()
        assert data["items"][0]["short_description"] == ""

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    @patch("courses.app.routes.courses.validate_pagination")
    def test_last_item_rotated_to_first(self, mock_validate, mock_list):
        courses = [make_course_row(course_id=f"id-{i}", course_title=f"Course {i}") for i in range(3)]
        mock_list.return_value = (3, courses)
        data = self.client.get("/courses/").json()
        assert data["items"][0]["course_id"] == "id-2"
        assert data["items"][1]["course_id"] == "id-0"
        assert data["items"][2]["course_id"] == "id-1"

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    @patch("courses.app.routes.courses.validate_pagination")
    def test_single_item_rotation_is_stable(self, mock_validate, mock_list):
        course = make_course_row(course_id="only-one")
        mock_list.return_value = (1, [course])
        data = self.client.get("/courses/").json()
        assert data["items"][0]["course_id"] == "only-one"

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    @patch("courses.app.routes.courses.validate_pagination")
    def test_empty_items_list(self, mock_validate, mock_list):
        mock_list.return_value = (0, [])
        data = self.client.get("/courses/").json()
        assert data["items"] == []
        assert data["total"] == 0

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    @patch("courses.app.routes.courses.validate_pagination")
    def test_pagination_meta_reflects_query_params(self, mock_validate, mock_list):
        mock_list.return_value = (50, [])
        data = self.client.get("/courses/?page=3&limit=5").json()
        assert data["page"] == 3
        assert data["limit"] == 5
        assert data["total"] == 50

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    @patch("courses.app.routes.courses.validate_pagination")
    def test_search_query_passed_to_crud(self, mock_validate, mock_list):
        mock_list.return_value = (0, [])
        self.client.get("/courses/?q=python")
        args = mock_list.call_args[0]
        # positional signature: list_courses(db, q, page, limit, ...)
        assert args[1] == "python"

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    @patch("courses.app.routes.courses.validate_pagination")
    def test_complexity_filter_passed_to_crud(self, mock_validate, mock_list):
        mock_list.return_value = (0, [])
        self.client.get("/courses/?complexity=advanced")
        args = mock_list.call_args[0]
        assert args[4] == "advanced"

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    @patch("courses.app.routes.courses.validate_pagination")
    def test_duration_filters_passed_to_crud(self, mock_validate, mock_list):
        mock_list.return_value = (0, [])
        self.client.get("/courses/?min_duration=30&max_duration=120")
        args = mock_list.call_args[0]
        assert args[5] == 30
        assert args[6] == 120

    @patch("courses.app.routes.courses.validate_pagination")
    def test_invalid_pagination_raises_400(self, mock_validate):
        mock_validate.side_effect = ValueError("limit exceeds max")
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
        self.app, self.mock_db = make_app()
        self.client = TestClient(self.app, raise_server_exceptions=False)

    @patch("courses.app.routes.courses.get_course", new_callable=AsyncMock)
    def test_returns_200_when_found(self, mock_get):
        mock_get.return_value = make_course_row()
        response = self.client.get("/courses/course-uuid-1")
        assert response.status_code == 200

    @patch("courses.app.routes.courses.get_course", new_callable=AsyncMock)
    def test_returns_404_when_not_found(self, mock_get):
        mock_get.return_value = None
        response = self.client.get("/courses/nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "Course not found"

    @patch("courses.app.routes.courses.get_course", new_callable=AsyncMock)
    def test_response_contains_all_fields(self, mock_get):
        mock_get.return_value = make_course_row()
        data = self.client.get("/courses/course-uuid-1").json()
        for field in [
            "course_id", "course_title", "course_desc", "course_duration",
            "course_complexity", "course_owner", "course_url",
            "course_redirect_url", "course_image_url", "course_credit", "created_at"
        ]:
            assert field in data, f"Missing field: {field}"

    @patch("courses.app.routes.courses.get_course", new_callable=AsyncMock)
    def test_created_at_is_isoformat_string(self, mock_get):
        mock_get.return_value = make_course_row(created_at=datetime(2024, 6, 1, 12, 0, 0))
        data = self.client.get("/courses/course-uuid-1").json()
        assert data["created_at"] == "2024-06-01T12:00:00"

    @patch("courses.app.routes.courses.get_course", new_callable=AsyncMock)
    def test_course_id_passed_to_crud(self, mock_get):
        mock_get.return_value = None
        self.client.get("/courses/my-specific-id")
        mock_get.assert_called_once()
        # FIXED: use call_args[0] for positional args — call_args.args also works
        # but call_args[0] is more universally compatible across Python versions.
        assert mock_get.call_args[0][1] == "my-specific-id"

    @patch("courses.app.routes.courses.get_course", new_callable=AsyncMock)
    def test_full_desc_returned_not_truncated(self, mock_get):
        long_desc = "D" * 500
        mock_get.return_value = make_course_row(course_desc=long_desc)
        data = self.client.get("/courses/course-uuid-1").json()
        assert len(data["course_desc"]) == 500

    @patch("courses.app.routes.courses.get_course", new_callable=AsyncMock)
    def test_course_credit_value(self, mock_get):
        mock_get.return_value = make_course_row(course_credit=5)
        data = self.client.get("/courses/course-uuid-1").json()
        assert data["course_credit"] == 5


# ─────────────────────────────────────────────
# Featured courses  GET /courses/featured
# NOTE: /featured must be registered BEFORE /{course_id} in the router
# ─────────────────────────────────────────────

class TestFeaturedCoursesEndpoint:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.app, self.mock_db = make_app()
        self.client = TestClient(self.app, raise_server_exceptions=False)

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    def test_returns_200(self, mock_list):
        mock_list.return_value = (3, [make_course_row() for _ in range(3)])
        response = self.client.get("/courses/featured")
        assert response.status_code == 200

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    def test_page_is_always_1(self, mock_list):
        mock_list.return_value = (2, [make_course_row(), make_course_row()])
        data = self.client.get("/courses/featured").json()
        assert data["page"] == 1

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    def test_crud_called_with_page_1(self, mock_list):
        mock_list.return_value = (0, [])
        self.client.get("/courses/featured")
        args = mock_list.call_args[0]
        assert args[2] == 1     # page
        assert args[1] is None  # q=None

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    def test_custom_limit_respected(self, mock_list):
        mock_list.return_value = (0, [])
        self.client.get("/courses/featured?limit=3")
        args = mock_list.call_args[0]
        assert args[3] == 3     # limit

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    def test_no_item_rotation_applied(self, mock_list):
        courses = [make_course_row(course_id=f"f-{i}") for i in range(3)]
        mock_list.return_value = (3, courses)
        data = self.client.get("/courses/featured").json()
        assert data["items"][0]["course_id"] == "f-0"

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    def test_short_description_truncated(self, mock_list):
        course = make_course_row(course_desc="Y" * 300)
        mock_list.return_value = (1, [course])
        data = self.client.get("/courses/featured").json()
        assert len(data["items"][0]["short_description"]) == 200

    @patch("courses.app.routes.courses.list_courses", new_callable=AsyncMock)
    def test_none_desc_becomes_empty_string(self, mock_list):
        course = make_course_row(course_desc=None)
        mock_list.return_value = (1, [course])
        data = self.client.get("/courses/featured").json()
        assert data["items"][0]["short_description"] == ""

    def test_limit_below_1_returns_422(self):
        response = self.client.get("/courses/featured?limit=0")
        assert response.status_code == 422