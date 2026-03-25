import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.get = AsyncMock()

    # Default execute result — overridable per test
    mock_result = MagicMock()
    mock_result.scalar.return_value = 0
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    mock_result.__iter__ = MagicMock(return_value=iter([]))
    session.execute = AsyncMock(return_value=mock_result)

    return session


@pytest.fixture
def client(mock_session):
    from flashcard.main import app
    from database import get_session

    async def override_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.unit
class TestRootEndpoint:

    def test_root_returns_ok(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["service"] == "flashcard-api"


@pytest.mark.unit
class TestFlashcardDecksListEndpoint:

    def test_returns_200(self, client, mock_session):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_result.scalars.return_value.all.return_value = []
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute = AsyncMock(return_value=mock_result)

        response = client.get("/flashcard-decks")
        assert response.status_code == 200

    def test_response_has_decks_and_pagination(self, client, mock_session):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_result.scalars.return_value.all.return_value = []
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute = AsyncMock(return_value=mock_result)

        data = client.get("/flashcard-decks").json()
        assert "decks" in data
        assert "pagination" in data

    def test_default_limit_is_6(self, client, mock_session):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_result.scalars.return_value.all.return_value = []
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute = AsyncMock(return_value=mock_result)

        data = client.get("/flashcard-decks").json()
        assert data["pagination"]["limit"] == 6

    def test_custom_offset_and_limit(self, client, mock_session):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_result.scalars.return_value.all.return_value = []
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute = AsyncMock(return_value=mock_result)

        data = client.get("/flashcard-decks?offset=6&limit=3").json()
        assert data["pagination"]["offset"] == 6
        assert data["pagination"]["limit"] == 3

    def test_limit_over_100_returns_422(self, client):
        response = client.get("/flashcard-decks?limit=200")
        assert response.status_code == 422


@pytest.mark.unit
class TestFlashcardDeckDetailEndpoint:

    def test_deck_not_found_returns_404(self, client, mock_session):
        mock_session.get = AsyncMock(return_value=None)
        response = client.get(f"/flashcard-decks/{str(uuid4())}")
        assert response.status_code == 404

    def test_deck_found_returns_200(self, client, mock_session):
        from flashcard.models import Quiz
        deck_id = str(uuid4())

        mock_deck = Quiz(
            title="Biology",
            subject_tag="Bio",
            difficulty_level="easy",
            description="Test",
        )
        mock_deck.quiz_id = deck_id

        mock_session.get = AsyncMock(return_value=mock_deck)

        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_result.scalars.return_value.all.return_value = []
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute = AsyncMock(return_value=mock_result)

        response = client.get(f"/flashcard-decks/{deck_id}")
        assert response.status_code == 200
        assert response.json()["deck_id"] == deck_id


@pytest.mark.unit
class TestFlashcardAnalyticsEndpoint:

    def test_missing_time_taken_returns_422(self, client):
        response = client.post("/flashcard-analytics", json={
            "deck_id": str(uuid4()), "user_id": "user-123",
        })
        assert response.status_code == 422

    def test_missing_deck_id_returns_422(self, client):
        response = client.post("/flashcard-analytics", json={
            "user_id": "user-123", "time_taken": 3.5,
        })
        assert response.status_code == 422
