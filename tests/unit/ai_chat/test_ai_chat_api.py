# tests/unit/ai_chat/test_ai_chat_api.py

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI


@pytest.fixture
def client():
    from ai_chat.app.routes.chat import router
    from ai_chat.app.utils.auth import get_current_user

    mock_user = MagicMock()
    mock_user.user_id = "test-user-123"

    app = FastAPI()
    app.include_router(router, prefix="/chat")
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_ai_chat_api(client, mocker):
    # ← FIXED: patch what the route actually calls — get_gemini_handler()
    mock_gemini = MagicMock()
    mock_gemini.generate_response.return_value = "Mocked API response"
    mocker.patch(
        "ai_chat.app.routes.chat.get_gemini_handler",
        return_value=mock_gemini
    )
    # Also patch session_memory and moderation so they don't interfere
    mocker.patch("ai_chat.app.routes.chat.session_memory")
    mocker.patch(
        "ai_chat.app.routes.chat.contains_harmful_content",
        return_value=False
    )

    response = client.post("/chat", json={"query": "Hello", "mode": "general"})

    assert response.status_code == 200
    assert response.json()["answer"] == "Mocked API response"