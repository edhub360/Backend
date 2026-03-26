import pytest
from ai_chat.app.modules.ai_chat.service import AIChatService  # added

@pytest.mark.asyncio
async def test_llm_client_mocked(mocker):
    mock_llm = mocker.patch(  # ← assigned to variable now
        "ai_chat.app.modules.ai_chat.service.LLMClient.generate",  # fixed path
        return_value="Mocked LLM output"
    )
    service = AIChatService()
    result = await service.get_response("Hello")
    assert result == "Mocked LLM output"
    mock_llm.assert_called_once()  # now mock_llm exists
