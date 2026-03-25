import pytest
@pytest.mark.asyncio
async def test_ai_chat_rag_context(mocker):
    mocker.patch(
        "app.modules.ai_chat.service.vector_store.search",
        return_value=["chunk1", "chunk2"]
    )

    mocker.patch(
        "app.modules.ai_chat.service.LLMClient.generate",
        return_value="Answer using RAG"
    )

    service = AIChatService()
    result = await service.get_response("Explain mitochondria")

    assert result == "Answer using RAG"
