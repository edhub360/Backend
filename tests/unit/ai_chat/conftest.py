import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


# ── Shared mock objects (imported by test files directly) ─────────────────

mock_user = MagicMock()
mock_user.user_id = "test-user-123"
mock_user.email = "test@edhub.com"
mock_user.username = "testuser"
mock_user.roles = ["student"]


# ── App-level client (full app, used for integration-style tests) ─────────

@pytest.fixture
def app_client():
    """
    Full-app TestClient with auth overridden.
    Named 'app_client' to avoid colliding with the router-level
    'client' fixture defined in test_ai_chat_routes.py.
    """
    from ai_chat.app.main import app as ai_chat_app
    from ai_chat.app.utils.auth import get_current_user

    ai_chat_app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(ai_chat_app) as c:
        yield c
    ai_chat_app.dependency_overrides.clear()


# ── AIChatService mock (opt-in via fixture param) ─────────────────────────

@pytest.fixture
def mock_ai_chat_service(monkeypatch):
    mock_service = MagicMock()
    mock_service.get_response = MagicMock(return_value="Mocked AI response")
    mock_service.stream_response = MagicMock(return_value=iter(["Mocked", " stream"]))
    monkeypatch.setattr(
        "ai_chat.app.routes.chat.AIChatService",
        MagicMock(return_value=mock_service)
    )
    return mock_service