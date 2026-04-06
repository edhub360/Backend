import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from uuid import uuid4


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def client(mock_session):
    from flashcard.main import app
    from flashcard.database import get_session
    app.dependency_overrides[get_session] = lambda: mock_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.unit
class TestFlashcardErrorHandling:

    def test_deck_not_found_returns_404(self, client):
        response = client.get(f"/flashcard-decks/{str(uuid4())}")
        assert response.status_code == 404

    def test_404_detail_message(self, client):
        deck_id = str(uuid4())
        response = client.get(f"/flashcard-decks/{deck_id}")
        assert "not found" in response.json()["detail"].lower()

    def test_analytics_invalid_json_returns_422(self, client):
        response = client.post("/flashcard-analytics", json={"invalid": "data"})
        assert response.status_code == 422

    def test_negative_offset_returns_422(self, client):
        response = client.get("/flashcard-decks?offset=-1")
        assert response.status_code == 422

    def test_zero_limit_returns_422(self, client):
        response = client.get("/flashcard-decks?limit=0")
        assert response.status_code == 422
