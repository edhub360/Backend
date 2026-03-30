import pytest
from uuid import uuid4

@pytest.mark.asyncio
async def test_ai_chat_api(client, mocker):
    mocker.patch(
        "ai_chat.app.modules.ai_chat.router.AIChatService.get_response",  # fixed path
        return_value="Mocked API response"
    )
    payload = {"message": "Hello"}
    response = await client.post("/ai/chat", json=payload)
    assert response.status_code == 200
    assert response.json()["response"] == "Mocked API response"
