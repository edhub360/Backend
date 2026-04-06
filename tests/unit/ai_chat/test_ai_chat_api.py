# tests/unit/ai_chat/test_ai_chat_api.py

import pytest
from unittest.mock import patch, MagicMock
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


def test_ai_chat_api(client, mocker):  # ← drop @pytest.mark.asyncio + async
    mocker.patch(
        "ai_chat.app.routes.chat.AIChatService.get_response",
        return_value="Mocked API response"
    )

    response = client.post("/chat", json={"query": "Hello", "mode": "general"})

    assert response.status_code == 200
    assert response.json()["answer"] == "Mocked API response"