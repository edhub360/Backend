import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def client(mock_session):
    from quiz.main import app
    from database import get_session
    app.dependency_overrides[get_session] = lambda: mock_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.unit
class TestRootEndpoint:

    def test_root_returns_ok(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.unit
class TestUserEndpoints:

    def test_get_user_not_found(self, client, mock_session):
        mock_session.get.return_value = None
        response = client.get(f"/users/{str(uuid4())}")
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_delete_user_not_found(self, client, mock_session):
        mock_session.get.return_value = None
        response = client.delete(f"/users/{str(uuid4())}")
        assert response.status_code == 404

    def test_update_user_not_found(self, client, mock_session):
        mock_session.get.return_value = None
        response = client.patch(
            f"/users/{str(uuid4())}",
            json={"name": "New Name"}
        )
        assert response.status_code == 404


@pytest.mark.unit
class TestQuizEndpoints:

    def test_get_quiz_not_found(self, client, mock_session):
        mock_session.get.return_value = None
        response = client.get(f"/quizzes/{str(uuid4())}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Quiz not found"

    def test_get_inactive_quiz_returns_404(self, client, mock_session):
        from quiz.models import Quiz
        inactive_quiz = Quiz(title="Inactive", is_active=False)
        mock_session.get.return_value = inactive_quiz
        response = client.get(f"/quizzes/{str(uuid4())}")
        assert response.status_code == 404

    def test_submit_attempt_user_not_found(self, client, mock_session):
        mock_session.get.return_value = None
        response = client.post("/quiz-attempts", json={
            "user_id": str(uuid4()),
            "quiz_id": str(uuid4()),
            "score": 8,
            "total_questions": 10,
            "score_percentage": 80.0,
            "time_taken": 120,
        })
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_create_quiz_missing_title_returns_422(self, client):
        response = client.post("/quizzes", json={"questions": []})
        assert response.status_code == 422

    def test_list_quizzes_invalid_limit_returns_422(self, client):
        response = client.get("/quizzes?limit=0")
        assert response.status_code == 422


@pytest.mark.unit
class TestDashboardEndpoints:

    def test_dashboard_summary_user_not_found(self, client, mock_session):
        mock_session.get.return_value = None
        response = client.get(f"/dashboard/summary?user_id={str(uuid4())}")
        assert response.status_code == 404

    def test_weekly_activity_user_not_found(self, client, mock_session):
        mock_session.get.return_value = None
        response = client.get(f"/dashboard/weekly-activity?user_id={str(uuid4())}")
        assert response.status_code == 404
