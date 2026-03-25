import pytest

@pytest.mark.asyncio
async def test_llm_client_mocked(mocker):
    from app.modules.ai_chat.service import AIChatService

    mocker.patch(
        "app.modules.ai_chat.service.LLMClient.generate",
        return_value="Mocked LLM output"
    )

    service = AIChatService()
    result = await service.get_response("Hello")

    assert result == "Mocked LLM output"
    mock_llm.assert_called_once()
