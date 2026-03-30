import pytest
@pytest.mark.asyncio
async def test_ai_chat_service_with_history(mocker):
    mocker.patch(
        "app.modules.ai_chat.service.LLMClient.generate",
        return_value="Context-aware answer"
    )

    service = AIChatService()

    history = [
        {"role": "user", "content": "What is gravity"},
        {"role": "assistant", "content": "Gravity is..."}
    ]

    result = await service.get_response("Explain again", history=history)

    assert result == "Context-aware answer"
