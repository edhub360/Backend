import pytest
from ai_chat.app.modules.ai_chat.service import AIChatService  # added

@pytest.mark.asyncio
async def test_ai_chat_parses_json(mocker):
    mocker.patch(
        "ai_chat.app.modules.ai_chat.service.LLMClient.generate",  # fixed path
        return_value='{"answer": "Hello", "confidence": 0.9}'
    )
    service = AIChatService()
    result = await service.get_response("Hi")
    assert result["answer"] == "Hello"
    assert result["confidence"] == 0.9
