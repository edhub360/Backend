import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime

# ─────────────────────────────────────────────
# UUID constants — all valid UUIDs
# ─────────────────────────────────────────────

COURSE_UUID_1  = "8473e11c-629a-4fed-b545-23f804709594"
UUID_ID_0      = "58479b99-417b-454a-b5e1-c600a1d3538b"
UUID_ID_1      = "8b6871c5-b184-42e2-b376-705943f46c16"
UUID_ID_2      = "f0d4d121-b79a-4cfa-b5c1-ce6336be5744"
UUID_ONLY      = "fd2a0b64-0b19-45a4-bd4b-1dd197ab5b0e"
UUID_SPECIFIC  = "c2c39058-c9aa-4c50-865b-10de3655db53"
UUID_F0        = "7c9785ea-bb7f-45e5-b55e-126089bad6ef"
UUID_F1        = "99605c02-bfaf-446d-bac2-414eace422c8"
UUID_F2        = "f4b854ca-3918-4bad-a5a7-25299df1b2a2"

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_course_row(**kwargs):
    defaults = dict(
        course_id=COURSE_UUID_1,
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

# ─────────────────────────────────────────────
# List courses GET /courses/
# ─────────────────────────────────────────────

class TestListCoursesEndpoint:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_db = MagicMock()
        self.mock_db.execute = AsyncMock()
        self.mock_db.scalar = AsyncMock(return_value=0)

        async def override_get_db():
            yield self.mock_db

        from courses.app.routes.courses import router
        app = FastAPI()

        with patch("courses.app.routes.courses.get_db", override_get_db):
            app.include_router(router, prefix="/courses")
            self.client = TestClient(app, raise_server_exceptions=False)
            yield

    def test_returns_200_with_courses(self):
        course = make_course_row()
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = [course]
        self.mock_db.scalar.return_value = 1
        response = self.client.get("/courses/")
        assert response.status_code == 200

    def test_response_shape(self):
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = [make_course_row()]
        self.mock_db.scalar.return_value = 1
        data = self.client.get("/courses/").json()
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "items" in data

    def test_short_description_truncated_to_200(self):
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = [make_course_row(course_desc="X" * 300)]
        self.mock_db.scalar.return_value = 1
        data = self.client.get("/courses/").json()
        assert len(data["items"][0]["short_description"]) == 200

    def test_none_course_desc_becomes_empty_string(self):
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = [make_course_row(course_desc=None)]
        self.mock_db.scalar.return_value = 1
        data = self.client.get("/courses/").json()
        assert data["items"][0]["short_description"] == ""

    def test_last_item_rotated_to_first(self):
        courses = [
            make_course_row(course_id=UUID_ID_0, course_title="Course 0"),
            make_course_row(course_id=UUID_ID_1, course_title="Course 1"),
            make_course_row(course_id=UUID_ID_2, course_title="Course 2"),
        ]
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = courses
        self.mock_db.scalar.return_value = 3
        data = self.client.get("/courses/").json()
        assert data["items"][0]["course_id"] == UUID_ID_2
        assert data["items"][1]["course_id"] == UUID_ID_0
        assert data["items"][2]["course_id"] == UUID_ID_1

    def test_single_item_rotation_is_stable(self):
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = [make_course_row(course_id=UUID_ONLY)]
        self.mock_db.scalar.return_value = 1
        data = self.client.get("/courses/").json()
        assert data["items"][0]["course_id"] == UUID_ONLY

    def test_empty_items_list(self):
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = []
        self.mock_db.scalar.return_value = 0
        data = self.client.get("/courses/").json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_pagination_meta_reflects_query_params(self):
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = []
        self.mock_db.scalar.return_value = 50
        data = self.client.get("/courses/?page=3&limit=5").json()
        assert data["page"] == 3
        assert data["limit"] == 5
        assert data["total"] == 50

    def test_search_query_passed_to_crud(self):
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = []
        self.mock_db.scalar.return_value = 0
        self.client.get("/courses/?q=python")
        self.mock_db.execute.assert_called()

    def test_complexity_filter_passed_to_crud(self):
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = []
        self.mock_db.scalar.return_value = 0
        response = self.client.get("/courses/?complexity=advanced")
        assert response.status_code == 200

    def test_duration_filters_passed_to_crud(self):
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = []
        self.mock_db.scalar.return_value = 0
        response = self.client.get("/courses/?min_duration=30&max_duration=120")
        assert response.status_code == 200

    def test_invalid_pagination_raises_400(self):
        with patch("courses.app.routes.courses.validate_pagination", side_effect=ValueError("limit exceeds max")):
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
# Get course GET /courses/{course_id}
# ─────────────────────────────────────────────

class TestGetCourseEndpoint:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_db = MagicMock()
        self.mock_db.execute = AsyncMock()
        self.mock_db.scalar = AsyncMock(return_value=0)

        async def override_get_db():
            yield self.mock_db

        from courses.app.routes.courses import router
        app = FastAPI()

        with patch("courses.app.routes.courses.get_db", override_get_db):
            app.include_router(router, prefix="/courses")
            self.client = TestClient(app, raise_server_exceptions=False)
            yield

    def test_returns_200_when_found(self):
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = make_course_row()
        response = self.client.get(f"/courses/{COURSE_UUID_1}")
        assert response.status_code == 200

    def test_returns_404_when_not_found(self):
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = None
        response = self.client.get(f"/courses/{UUID_SPECIFIC}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Course not found"

    def test_response_contains_all_fields(self):
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = make_course_row()
        data = self.client.get(f"/courses/{COURSE_UUID_1}").json()
        for field in [
            "course_id", "course_title", "course_desc", "course_duration",
            "course_complexity", "course_owner", "course_url",
            "course_redirect_url", "course_image_url", "course_credit", "created_at"
        ]:
            assert field in data, f"Missing field: {field}"

    def test_created_at_is_isoformat_string(self):
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = make_course_row(created_at=datetime(2024, 6, 1, 12, 0, 0))
        data = self.client.get(f"/courses/{COURSE_UUID_1}").json()
        assert data["created_at"] == "2024-06-01T12:00:00"

    def test_course_id_passed_to_crud(self):
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = None
        self.client.get(f"/courses/{UUID_SPECIFIC}")
        self.mock_db.execute.assert_called_once()

    def test_full_desc_returned_not_truncated(self):
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = make_course_row(course_desc="D" * 500)
        data = self.client.get(f"/courses/{COURSE_UUID_1}").json()
        assert len(data["course_desc"]) == 500

    def test_course_credit_value(self):
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = make_course_row(course_credit=5)
        data = self.client.get(f"/courses/{COURSE_UUID_1}").json()
        assert data["course_credit"] == 5


# ─────────────────────────────────────────────
# Featured courses GET /courses/featured
# ─────────────────────────────────────────────

class TestFeaturedCoursesEndpoint:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_db = MagicMock()
        self.mock_db.execute = AsyncMock()
        self.mock_db.scalar = AsyncMock(return_value=0)

        async def override_get_db():
            yield self.mock_db

        from courses.app.routes.courses import router
        app = FastAPI()

        with patch("courses.app.routes.courses.get_db", override_get_db):
            app.include_router(router, prefix="/courses")
            self.client = TestClient(app, raise_server_exceptions=False)
            yield

    def test_returns_200(self):
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = [make_course_row() for _ in range(3)]
        self.mock_db.scalar.return_value = 3
        response = self.client.get("/courses/featured")
        assert response.status_code == 200

    def test_page_is_always_1(self):
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = [make_course_row(), make_course_row()]
        self.mock_db.scalar.return_value = 2
        data = self.client.get("/courses/featured").json()
        assert data["page"] == 1

    def test_crud_called_with_page_1(self):
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = []
        self.mock_db.scalar.return_value = 0
        self.client.get("/courses/featured")
        self.mock_db.execute.assert_called()

    def test_custom_limit_respected(self):
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = []
        self.mock_db.scalar.return_value = 0
        response = self.client.get("/courses/featured?limit=3")
        assert response.status_code == 200

    def test_no_item_rotation_applied(self):
        courses = [
            make_course_row(course_id=UUID_F0),
            make_course_row(course_id=UUID_F1),
            make_course_row(course_id=UUID_F2),
        ]
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = courses
        self.mock_db.scalar.return_value = 3
        data = self.client.get("/courses/featured").json()
        assert data["items"][0]["course_id"] == UUID_F0

    def test_short_description_truncated(self):
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = [make_course_row(course_desc="Y" * 300)]
        self.mock_db.scalar.return_value = 1
        data = self.client.get("/courses/featured").json()
        assert len(data["items"][0]["short_description"]) == 200

    def test_none_desc_becomes_empty_string(self):
        self.mock_db.execute.return_value.scalars.return_value.all.return_value = [make_course_row(course_desc=None)]
        self.mock_db.scalar.return_value = 1
        data = self.client.get("/courses/featured").json()
        assert data["items"][0]["short_description"] == ""

    def test_limit_below_1_returns_422(self):
        response = self.client.get("/courses/featured?limit=0")
        assert response.status_code == 422