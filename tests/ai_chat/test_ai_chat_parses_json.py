@pytest.mark.asyncio
async def test_ai_chat_parses_json(mocker):
    mocker.patch(
        "app.modules.ai_chat.service.LLMClient.generate",
        return_value='{"answer": "Hello", "confidence": 0.9}'
    )

    service = AIChatService()
    result = await service.get_response("Hi")

    assert result["answer"] == "Hello"
    assert result["confidence"] == 0.9
