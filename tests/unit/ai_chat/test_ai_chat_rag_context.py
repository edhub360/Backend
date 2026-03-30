import pytest
from ai_chat.app.modules.ai_chat.service import AIChatService  # added

@pytest.mark.asyncio
async def test_ai_chat_rag_context(mocker):
    mocker.patch(
        "ai_chat.app.modules.ai_chat.service.vector_store.search",  # fixed path
        return_value=["chunk1", "chunk2"]
    )
    mocker.patch(
        "ai_chat.app.modules.ai_chat.service.LLMClient.generate",  # fixed path
        return_value="Answer using RAG"
    )
    service = AIChatService()
    result = await service.get_response("Explain mitochondria")
    assert result == "Answer using RAG"
