import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_ai_chat_api(client, mocker):
    # Patch the instance method on the class — works regardless of how
    # the router instantiates AIChatService
    mocker.patch(
        "ai_chat.app.routes.chat.AIChatService.get_response",
        return_value="Mocked API response"
    )

    payload = {"query": "Hello", "mode": "general"}  # ← correct field names

    response = client.post("/chat", json=payload)     # ← correct prefix + sync client

    assert response.status_code == 200
    assert response.json()["answer"] == "Mocked API response"  # ← response key is "answer"