import pytest
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.main import app
from app.api.deps import DBSessionDep, CurrentUserDep
from tests.study_planner.conftest import make_mock_user, make_mock_db

USER_ID = uuid4()
PLAN_ID = uuid4()
ITEM_ID = uuid4()
SVC = "app.api.v1.study_plan.svc"


def setup_client():
    app.dependency_overrides[DBSessionDep] = lambda: make_mock_db()
    app.dependency_overrides[CurrentUserDep] = lambda: make_mock_user(USER_ID)
    return TestClient(app)


def teardown():
    app.dependency_overrides.clear()


class TestHealthCheck:
    def test_ok(self):
        c = setup_client()
        assert c.get("/health").json() == {"status": "ok"}
        teardown()


class TestCreatePlan:
    def test_missing_name_422(self):
        c = setup_client()
        with patch(f"{SVC}.create_study_plan", new_callable=AsyncMock):
            assert c.post("/api/v1/study-plan/", json={}).status_code == 422
        teardown()


class TestListPlans:
    def test_returns_empty_list(self):
        c = setup_client()
        with patch(f"{SVC}.list_study_plans", new=AsyncMock(return_value=[])):
            r = c.get("/api/v1/study-plan/")
        teardown()
        assert r.status_code == 200
        assert r.json() == []


class TestGetPlan:
    def test_404(self):
        c = setup_client()
        with patch(f"{SVC}.get_study_plan_or_404",
                   new=AsyncMock(side_effect=HTTPException(404, "Study plan not found"))):
            assert c.get(f"/api/v1/study-plan/{uuid4()}").status_code == 404
        teardown()


class TestUpdatePlan:
    def test_predefined_403(self):
        c = setup_client()
        with patch(f"{SVC}.update_study_plan",
                   new=AsyncMock(side_effect=HTTPException(403, "Cannot update predefined plans"))):
            assert c.patch(f"/api/v1/study-plan/{PLAN_ID}", json={"name": "X"}).status_code == 403
        teardown()


class TestDeletePlan:
    def test_204(self):
        c = setup_client()
        with patch(f"{SVC}.delete_study_plan", new=AsyncMock(return_value=None)):
            assert c.delete(f"/api/v1/study-plan/{PLAN_ID}").status_code == 204
        teardown()

    def test_predefined_403(self):
        c = setup_client()
        with patch(f"{SVC}.delete_study_plan",
                   new=AsyncMock(side_effect=HTTPException(403, "Cannot delete predefined plans"))):
            assert c.delete(f"/api/v1/study-plan/{PLAN_ID}").status_code == 403
        teardown()


class TestCreateFromPredefined:
    def test_predefined_not_found_404(self):
        c = setup_client()
        with patch(f"{SVC}.create_from_predefined",
                   new=AsyncMock(side_effect=HTTPException(404, "Predefined plan not found"))):
            assert c.post(f"/api/v1/study-plan/{PLAN_ID}/from-predefined",
                          json={"name": "Copy"}).status_code == 404
        teardown()

    def test_missing_name_422(self):
        c = setup_client()
        with patch(f"{SVC}.create_from_predefined", new_callable=AsyncMock):
            assert c.post(f"/api/v1/study-plan/{PLAN_ID}/from-predefined",
                          json={}).status_code == 422
        teardown()


class TestCreateItem:
    def test_missing_fields_422(self):
        c = setup_client()
        assert c.post("/api/v1/study-plan/items", json={}).status_code == 422
        teardown()

    def test_plan_not_visible_404(self):
        c = setup_client()
        with patch(f"{SVC}.create_study_item",
                   new=AsyncMock(side_effect=HTTPException(404, "Study plan not found"))):
            assert c.post("/api/v1/study-plan/items",
                          json={"course_code": "CS101", "title": "T",
                                "study_plan_id": str(uuid4())}).status_code == 404
        teardown()


class TestListItems:
    def test_200(self):
        c = setup_client()
        with patch(f"{SVC}.list_study_items", new=AsyncMock(return_value=[])):
            assert c.get("/api/v1/study-plan/items").status_code == 200
        teardown()


class TestGetItem:
    def test_404(self):
        c = setup_client()
        with patch(f"{SVC}.get_study_item_or_404",
                   new=AsyncMock(side_effect=HTTPException(404, "Study item not found"))):
            assert c.get(f"/api/v1/study-plan/items/{uuid4()}").status_code == 404
        teardown()


class TestUpdateItem:
    def test_not_owned_403(self):
        c = setup_client()
        with patch(f"{SVC}.update_study_item",
                   new=AsyncMock(side_effect=HTTPException(403, "Cannot update items from predefined plans"))):
            assert c.patch(f"/api/v1/study-plan/items/{ITEM_ID}", json={"title": "H"}).status_code == 403
        teardown()


class TestDeleteItem:
    def test_204(self):
        c = setup_client()
        with patch(f"{SVC}.delete_study_item", new=AsyncMock(return_value=None)):
            assert c.delete(f"/api/v1/study-plan/items/{ITEM_ID}").status_code == 204
        teardown()

    def test_not_owned_403(self):
        c = setup_client()
        with patch(f"{SVC}.delete_study_item",
                   new=AsyncMock(side_effect=HTTPException(403, "Cannot delete items from predefined plans"))):
            assert c.delete(f"/api/v1/study-plan/items/{ITEM_ID}").status_code == 403
        teardown()


class TestGetItemsByPlan:
    def test_200(self):
        c = setup_client()
        with patch(f"{SVC}.get_study_items_by_plan_id", new=AsyncMock(return_value=[])):
            assert c.get(f"/api/v1/study-plan/{PLAN_ID}/items").status_code == 200
        teardown()

    def test_plan_not_found_404(self):
        c = setup_client()
        with patch(f"{SVC}.get_study_items_by_plan_id",
                   new=AsyncMock(side_effect=HTTPException(404, "Study plan not found"))):
            assert c.get(f"/api/v1/study-plan/{uuid4()}/items").status_code == 404
        teardown()


class TestListCourses:
    def test_200(self):
        c = setup_client()
        with patch(f"{SVC}.list_courses", new=AsyncMock(return_value=[])):
            assert c.get("/api/v1/study-plan/courses").status_code == 200
        teardown()

    def test_search_query(self):
        c = setup_client()
        with patch(f"{SVC}.list_courses", new=AsyncMock(return_value=[])):
            assert c.get("/api/v1/study-plan/courses?q=python").status_code == 200
        teardown()


class TestGetSummary:
    def test_returns_terms(self):
        c = setup_client()
        with patch(f"{SVC}.compute_summary",
                   new=AsyncMock(return_value={"terms": [{"term_name": "T1", "course_count": 3}]})):
            r = c.get("/api/v1/study-plan/summary")
        teardown()
        assert r.status_code == 200
        assert r.json()["terms"][0]["term_name"] == "T1"

    def test_empty_summary(self):
        c = setup_client()
        with patch(f"{SVC}.compute_summary", new=AsyncMock(return_value={"terms": []})):
            r = c.get("/api/v1/study-plan/summary")
        teardown()
        assert r.json() == {"terms": []}