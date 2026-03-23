@pytest.mark.asyncio
async def test_ai_chat_handles_llm_error(mocker):
    mocker.patch(
        "app.modules.ai_chat.service.LLMClient.generate",
        side_effect=Exception("LLM timeout")
    )

    service = AIChatService()
    result = await service.get_response("Hello")

    assert "error" in result.lower()
