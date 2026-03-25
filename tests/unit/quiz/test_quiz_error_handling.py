import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def client(mock_session):
    from quiz.main import app
    from database import get_session
    app.dependency_overrides[get_session] = lambda: mock_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.unit
class TestQuizErrorHandling:

    def test_get_nonexistent_user_returns_404(self, client):
        response = client.get(f"/users/{str(uuid4())}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_nonexistent_quiz_returns_404(self, client):
        response = client.get(f"/quizzes/{str(uuid4())}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_invalid_payload_returns_422(self, client):
        response = client.post("/users", json={"email": "bad-email"})
        assert response.status_code == 422

    def test_attempt_missing_score_returns_422(self, client):
        response = client.post("/quiz-attempts", json={
            "user_id": str(uuid4()),
            "quiz_id": str(uuid4()),
        })
        assert response.status_code == 422

    def test_list_quizzes_negative_offset_returns_422(self, client):
        response = client.get("/quizzes?offset=-1")
        assert response.status_code == 422

    def test_list_quizzes_limit_over_100_returns_422(self, client):
        response = client.get("/quizzes?limit=101")
        assert response.status_code == 422
