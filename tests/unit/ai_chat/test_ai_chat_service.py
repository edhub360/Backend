# test_ai_chat_service.py
import pytest
from ai_chat.app.modules.ai_chat.service import AIChatService

@pytest.mark.asyncio
async def test_ai_chat_service_with_history(mocker):
    mocker.patch(
        "ai_chat.service.LLMClient.generate",  # ← patch path must match import path
        return_value="Context-aware answer"
    )
    service = AIChatService()
    history = [
        {"role": "user", "content": "What is gravity"},
        {"role": "assistant", "content": "Gravity is..."}
    ]
    result = await service.get_response("Explain again", history=history)
    assert result == "Context-aware answer"