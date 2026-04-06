import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime
from uuid import uuid4


# ============================================================
# SECTION 1: Analytics Model Behavior
# ============================================================

@pytest.mark.unit
class TestFlashcardAnalyticsModelBehavior:

    def test_analytics_stores_correct_deck_id(self):
        from flashcard.models import FlashcardAnalytics
        deck_id = str(uuid4())
        a = FlashcardAnalytics(deck_id=deck_id, user_id="u1", time_taken=3.0)
        assert a.deck_id == deck_id

    def test_analytics_stores_correct_user_id(self):
        from flashcard.models import FlashcardAnalytics
        a = FlashcardAnalytics(deck_id=str(uuid4()), user_id="user-xyz", time_taken=2.0)
        assert a.user_id == "user-xyz"

    def test_analytics_card_reviewed_true_by_default(self):
        from flashcard.models import FlashcardAnalytics
        a = FlashcardAnalytics(deck_id=str(uuid4()), user_id="u1", time_taken=1.0)
        assert a.card_reviewed is True

    def test_analytics_card_reviewed_can_be_false(self):
        from flashcard.models import FlashcardAnalytics
        a = FlashcardAnalytics(
            deck_id=str(uuid4()),
            user_id="u1",
            time_taken=1.0,
            card_reviewed=False,
        )
        assert a.card_reviewed is False

    def test_analytics_time_taken_stores_decimal(self):
        from flashcard.models import FlashcardAnalytics
        a = FlashcardAnalytics(deck_id=str(uuid4()), user_id="u1", time_taken=7.35)
        assert a.time_taken == 7.35

    def test_two_analytics_entries_independent(self):
        from flashcard.models import FlashcardAnalytics
        a1 = FlashcardAnalytics(deck_id=str(uuid4()), user_id="u1", time_taken=2.0)
        a2 = FlashcardAnalytics(deck_id=str(uuid4()), user_id="u2", time_taken=5.0)
        assert a1.user_id != a2.user_id
        assert a1.time_taken != a2.time_taken


# ============================================================
# SECTION 2: Analytics Schema Validation
# ============================================================

@pytest.mark.unit
class TestFlashcardAnalyticsSchemaValidation:

    def test_valid_payload(self):
        from flashcard.schemas import FlashcardAnalyticsCreate
        payload = FlashcardAnalyticsCreate(
            deck_id=str(uuid4()),
            user_id="user-123",
            card_reviewed=True,
            time_taken=4.5,
        )
        assert payload.deck_id is not None
        assert payload.user_id == "user-123"
        assert payload.time_taken == 4.5

    def test_card_reviewed_defaults_true(self):
        from flashcard.schemas import FlashcardAnalyticsCreate
        payload = FlashcardAnalyticsCreate(
            deck_id=str(uuid4()), user_id="u1", time_taken=2.0
        )
        assert payload.card_reviewed is True

    def test_card_not_reviewed(self):
        from flashcard.schemas import FlashcardAnalyticsCreate
        payload = FlashcardAnalyticsCreate(
            deck_id=str(uuid4()), user_id="u1",
            time_taken=2.0, card_reviewed=False,
        )
        assert payload.card_reviewed is False

    def test_missing_time_taken_raises(self):
        from flashcard.schemas import FlashcardAnalyticsCreate
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            FlashcardAnalyticsCreate(deck_id=str(uuid4()), user_id="u1")

    def test_missing_user_id_raises(self):
        from flashcard.schemas import FlashcardAnalyticsCreate
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            FlashcardAnalyticsCreate(deck_id=str(uuid4()), time_taken=2.0)

    def test_missing_deck_id_raises(self):
        from flashcard.schemas import FlashcardAnalyticsCreate
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            FlashcardAnalyticsCreate(user_id="u1", time_taken=2.0)

    def test_analytics_out_schema_valid(self):
        from flashcard.schemas import FlashcardAnalyticsOut
        out = FlashcardAnalyticsOut(
            analytics_id=str(uuid4()),
            deck_id=str(uuid4()),
            user_id="user-123",
            card_reviewed=True,
            time_taken=3.5,
            reviewed_at=datetime.utcnow(),
        )
        assert isinstance(out.reviewed_at, datetime)
        assert out.time_taken == 3.5

    def test_analytics_out_reviewed_at_is_datetime(self):
        from flashcard.schemas import FlashcardAnalyticsOut
        out = FlashcardAnalyticsOut(
            analytics_id=str(uuid4()),
            deck_id=str(uuid4()),
            user_id="u1",
            card_reviewed=True,
            time_taken=1.0,
            reviewed_at=datetime.utcnow(),
        )
        assert isinstance(out.reviewed_at, datetime)


# ============================================================
# SECTION 3: Analytics API Endpoint
# ============================================================

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def client(mock_session):
    from flashcard.main import app
    from flashcard.database import get_session
    app.dependency_overrides[get_session] = lambda: mock_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.unit
class TestFlashcardAnalyticsAPIEndpoint:

    def test_valid_analytics_returns_201(self, client, mock_session):
        deck_id = str(uuid4())
        analytics_id = str(uuid4())

        async def mock_refresh(obj):
            obj.analytics_id = analytics_id
            obj.reviewed_at = datetime.utcnow()

        mock_session.refresh = mock_refresh
        response = client.post("/flashcard-analytics", json={
            "deck_id": deck_id,
            "user_id": "user-123",
            "card_reviewed": True,
            "time_taken": 4.5,
        })
        assert response.status_code == 201

    def test_missing_time_taken_returns_422(self, client):
        response = client.post("/flashcard-analytics", json={
            "deck_id": str(uuid4()),
            "user_id": "user-123",
        })
        assert response.status_code == 422

    def test_missing_user_id_returns_422(self, client):
        response = client.post("/flashcard-analytics", json={
            "deck_id": str(uuid4()),
            "time_taken": 3.0,
        })
        assert response.status_code == 422

    def test_missing_deck_id_returns_422(self, client):
        response = client.post("/flashcard-analytics", json={
            "user_id": "user-123",
            "time_taken": 3.0,
        })
        assert response.status_code == 422

    def test_empty_payload_returns_422(self, client):
        response = client.post("/flashcard-analytics", json={})
        assert response.status_code == 422

    def test_card_not_reviewed_accepted(self, client, mock_session):
        async def mock_refresh(obj):
            obj.analytics_id = str(uuid4())
            obj.reviewed_at = datetime.utcnow()

        mock_session.refresh = mock_refresh
        response = client.post("/flashcard-analytics", json={
            "deck_id": str(uuid4()),
            "user_id": "user-123",
            "card_reviewed": False,
            "time_taken": 2.0,
        })
        assert response.status_code == 201
