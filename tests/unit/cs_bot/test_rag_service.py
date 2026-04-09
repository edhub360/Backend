"""tests/unit/cs_bot/test_rag_service.py"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage


class TestFormatDocs:

    def test_joins_page_content_with_double_newline(self):
        from app.services.rag_service import _format_docs
        docs   = [MagicMock(page_content="chunk1"), MagicMock(page_content="chunk2")]
        result = _format_docs(docs)
        assert result == "chunk1\n\nchunk2"

    def test_single_doc_no_separator(self):
        from app.services.rag_service import _format_docs
        docs   = [MagicMock(page_content="only one")]
        assert _format_docs(docs) == "only one"

    def test_empty_docs_returns_empty_string(self):
        from app.services.rag_service import _format_docs
        assert _format_docs([]) == ""


class TestGetLlm:

    def test_returns_llm_instance(self):
        mock_llm = MagicMock()
        with patch("app.services.rag_service.ChatGoogleGenerativeAI",
                   return_value=mock_llm) as mock_cls,              patch("app.services.rag_service.settings") as s:
            s.CHAT_MODEL     = "gemini-2.5-flash"
            s.GEMINI_API_KEY = "fake-key"
            from app.services.rag_service import get_llm
            llm = get_llm()
        assert llm is mock_llm

    def test_uses_correct_model(self):
        with patch("app.services.rag_service.ChatGoogleGenerativeAI") as mock_cls,              patch("app.services.rag_service.settings") as s:
            s.CHAT_MODEL     = "gemini-2.5-flash"
            s.GEMINI_API_KEY = "fake-key"
            from app.services.rag_service import get_llm
            get_llm()
        kwargs = mock_cls.call_args[1]
        assert kwargs["model"]       == "gemini-2.5-flash"
        assert kwargs["temperature"] == 0


class TestGenerateReply:

    def _make_chain(self, reply="Test answer"):
        """Build a mock chain that returns reply from ainvoke."""
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=reply)
        return mock_chain

    def _setup_pipeline(self, mock_chain):
        """Wire up prompt | llm | parser to return mock_chain."""
        mock_prompt  = MagicMock()
        mock_llm     = MagicMock()
        mock_parser  = MagicMock()
        pipe_mid     = MagicMock()
        pipe_mid.__or__ = MagicMock(return_value=mock_chain)
        mock_prompt.__or__ = MagicMock(return_value=pipe_mid)
        return mock_prompt, mock_llm, mock_parser

    @pytest.mark.asyncio
    async def test_returns_reply_string(self, mock_vector_store):
        mock_retriever        = AsyncMock()
        mock_retriever.ainvoke = AsyncMock(return_value=[
            MagicMock(page_content="Edhub info",
                      metadata={"source": "https://edhub.com"})
        ])
        mock_vector_store.as_retriever.return_value = mock_retriever

        mock_chain   = self._make_chain("Edhub is great.")
        mock_prompt, mock_llm, mock_parser = self._setup_pipeline(mock_chain)

        with patch("app.services.rag_service.get_vector_store",
                   return_value=mock_vector_store),              patch("app.services.rag_service.get_llm",          return_value=mock_llm),              patch("app.services.rag_service.ChatPromptTemplate.from_messages",
                   return_value=mock_prompt),              patch("app.services.rag_service.StrOutputParser",  return_value=mock_parser):
            from app.services.rag_service import generate_reply
            reply, sources = await generate_reply("What is Edhub?", [])

        assert reply == "Edhub is great."

    @pytest.mark.asyncio
    async def test_returns_sources_list(self, mock_vector_store):
        mock_retriever        = AsyncMock()
        mock_retriever.ainvoke = AsyncMock(return_value=[
            MagicMock(page_content="text", metadata={"source": "https://edhub.com"}),
        ])
        mock_vector_store.as_retriever.return_value = mock_retriever

        mock_chain   = self._make_chain("reply")
        mock_prompt, mock_llm, mock_parser = self._setup_pipeline(mock_chain)

        with patch("app.services.rag_service.get_vector_store",
                   return_value=mock_vector_store),              patch("app.services.rag_service.get_llm",          return_value=mock_llm),              patch("app.services.rag_service.ChatPromptTemplate.from_messages",
                   return_value=mock_prompt),              patch("app.services.rag_service.StrOutputParser",  return_value=mock_parser):
            from app.services.rag_service import generate_reply
            _, sources = await generate_reply("question", [])

        assert "https://edhub.com" in sources

    @pytest.mark.asyncio
    async def test_sources_are_deduplicated(self, mock_vector_store):
        mock_retriever        = AsyncMock()
        mock_retriever.ainvoke = AsyncMock(return_value=[
            MagicMock(page_content="t1", metadata={"source": "https://same.com"}),
            MagicMock(page_content="t2", metadata={"source": "https://same.com"}),
        ])
        mock_vector_store.as_retriever.return_value = mock_retriever

        mock_chain   = self._make_chain("reply")
        mock_prompt, mock_llm, mock_parser = self._setup_pipeline(mock_chain)

        with patch("app.services.rag_service.get_vector_store",
                   return_value=mock_vector_store),              patch("app.services.rag_service.get_llm",          return_value=mock_llm),              patch("app.services.rag_service.ChatPromptTemplate.from_messages",
                   return_value=mock_prompt),              patch("app.services.rag_service.StrOutputParser",  return_value=mock_parser):
            from app.services.rag_service import generate_reply
            _, sources = await generate_reply("question", [])

        assert len(sources) == 1

    @pytest.mark.asyncio
    async def test_docs_without_source_excluded(self, mock_vector_store):
        mock_retriever        = AsyncMock()
        mock_retriever.ainvoke = AsyncMock(return_value=[
            MagicMock(page_content="text", metadata={}),
        ])
        mock_vector_store.as_retriever.return_value = mock_retriever

        mock_chain   = self._make_chain("reply")
        mock_prompt, mock_llm, mock_parser = self._setup_pipeline(mock_chain)

        with patch("app.services.rag_service.get_vector_store",
                   return_value=mock_vector_store),              patch("app.services.rag_service.get_llm",          return_value=mock_llm),              patch("app.services.rag_service.ChatPromptTemplate.from_messages",
                   return_value=mock_prompt),              patch("app.services.rag_service.StrOutputParser",  return_value=mock_parser):
            from app.services.rag_service import generate_reply
            _, sources = await generate_reply("question", [])

        assert sources == []

    @pytest.mark.asyncio
    async def test_history_passed_to_chain(self, mock_vector_store):
        mock_retriever        = AsyncMock()
        mock_retriever.ainvoke = AsyncMock(return_value=[])
        mock_vector_store.as_retriever.return_value = mock_retriever

        mock_chain   = self._make_chain("reply")
        mock_prompt, mock_llm, mock_parser = self._setup_pipeline(mock_chain)

        history = [HumanMessage(content="prev question"), AIMessage(content="prev answer")]

        with patch("app.services.rag_service.get_vector_store",
                   return_value=mock_vector_store),              patch("app.services.rag_service.get_llm",          return_value=mock_llm),              patch("app.services.rag_service.ChatPromptTemplate.from_messages",
                   return_value=mock_prompt),              patch("app.services.rag_service.StrOutputParser",  return_value=mock_parser):
            from app.services.rag_service import generate_reply
            await generate_reply("new question", history)

        call_kwargs = mock_chain.ainvoke.call_args[0][0]
        assert call_kwargs["history"] == history
        assert call_kwargs["question"] == "new question"
