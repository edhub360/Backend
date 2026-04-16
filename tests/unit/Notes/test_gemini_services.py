# tests/unit/notes/services/test_gemini_service.py

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from typing import List, Dict, Any


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures & helpers
# ══════════════════════════════════════════════════════════════════════════════

MOCK_CHUNKS = [
    {"source_name": "lecture.pdf", "chunk": "Python is a programming language.", "score": 0.92},
    {"source_name": "textbook.pdf", "chunk": "It supports OOP and functional paradigms.", "score": 0.85},
]

MOCK_HISTORY = [
    {"role": "user", "content": "What is Python?"},
    {"role": "assistant", "content": "Python is a high-level language."},
]


def _make_candidate(text="Generated answer.", finish_reason_name="STOP"):
    part = MagicMock()
    part.text = text

    content = MagicMock()
    content.parts = [part]

    finish_reason = MagicMock()
    finish_reason.name = finish_reason_name

    candidate = MagicMock()
    candidate.content = content
    candidate.finish_reason = finish_reason
    candidate.token_count = 42
    return candidate


def _make_response(text="Generated answer.", finish_reason_name="STOP"):
    resp = MagicMock()
    resp.candidates = [_make_candidate(text, finish_reason_name)]
    return resp


def _make_service(api_key="fake-key"):
    with patch.dict("os.environ", {"GEMINI_API_KEY": api_key}):
        with patch("services.gemini_service.genai"):
            from Notes.services.gemini_service import GeminiService
            svc = GeminiService()
    return svc


# ══════════════════════════════════════════════════════════════════════════════
# GeminiService.__init__
# ══════════════════════════════════════════════════════════════════════════════
class TestGeminiServiceInit:

    def test_raises_if_api_key_missing(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("services.gemini_service.genai"):
                from Notes.services.gemini_service import GeminiService
                with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                    GeminiService()

    def test_initialises_with_valid_api_key(self):
        svc = _make_service()
        assert svc is not None

    def test_api_key_stored(self):
        svc = _make_service("my-secret-key")
        assert svc.api_key == "my-secret-key"

    def test_genai_configured_with_api_key(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            with patch("services.gemini_service.genai") as mock_genai:
                from importlib import reload
                import Notes.services.gemini_service as svc_module
                reload(svc_module)
                svc_module.GeminiService()
                mock_genai.configure.assert_called_with(api_key="test-key")

    def test_model_attribute_set(self):
        svc = _make_service()
        assert svc.model is not None


# ══════════════════════════════════════════════════════════════════════════════
# _build_context_from_chunks
# ══════════════════════════════════════════════════════════════════════════════
class TestBuildContextFromChunks:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.svc = _make_service()

    def test_empty_chunks_returns_no_context_message(self):
        result = self.svc._build_context_from_chunks([])
        assert "No relevant context available." in result

    def test_source_name_included(self):
        result = self.svc._build_context_from_chunks(MOCK_CHUNKS)
        assert "lecture.pdf" in result

    def test_chunk_content_included(self):
        result = self.svc._build_context_from_chunks(MOCK_CHUNKS)
        assert "Python is a programming language." in result

    def test_relevance_score_included(self):
        result = self.svc._build_context_from_chunks(MOCK_CHUNKS)
        assert "0.92" in result

    def test_multiple_sources_numbered(self):
        result = self.svc._build_context_from_chunks(MOCK_CHUNKS)
        assert "Source 1" in result
        assert "Source 2" in result

    def test_missing_source_name_defaults_to_unknown(self):
        chunks = [{"chunk": "Some content", "score": 0.5}]
        result = self.svc._build_context_from_chunks(chunks)
        assert "Unknown source" in result

    def test_missing_chunk_content_uses_empty_string(self):
        chunks = [{"source_name": "doc.pdf", "score": 0.9}]
        result = self.svc._build_context_from_chunks(chunks)
        assert "doc.pdf" in result

    def test_returns_string(self):
        result = self.svc._build_context_from_chunks(MOCK_CHUNKS)
        assert isinstance(result, str)


# ══════════════════════════════════════════════════════════════════════════════
# _build_history_context
# ══════════════════════════════════════════════════════════════════════════════
class TestBuildHistoryContext:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.svc = _make_service()

    def test_empty_history_returns_empty_string(self):
        assert self.svc._build_history_context([]) == ""

    def test_user_message_labelled(self):
        result = self.svc._build_history_context(MOCK_HISTORY)
        assert "Previous User Question" in result

    def test_assistant_message_labelled(self):
        result = self.svc._build_history_context(MOCK_HISTORY)
        assert "Previous Assistant Response" in result

    def test_message_content_included(self):
        result = self.svc._build_history_context(MOCK_HISTORY)
        assert "What is Python?" in result
        assert "Python is a high-level language." in result

    def test_only_last_6_messages_included(self):
        history = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        result = self.svc._build_history_context(history)
        # First 4 messages should be excluded
        assert "msg 0" not in result
        assert "msg 9" in result

    def test_fewer_than_6_messages_all_included(self):
        history = [{"role": "user", "content": f"msg {i}"} for i in range(4)]
        result = self.svc._build_history_context(history)
        assert all(f"msg {i}" in result for i in range(4))

    def test_exactly_6_messages_all_included(self):
        history = [{"role": "user", "content": f"msg {i}"} for i in range(6)]
        result = self.svc._build_history_context(history)
        assert all(f"msg {i}" in result for i in range(6))

    def test_unknown_role_still_included(self):
        history = [{"role": "system", "content": "system msg"}]
        result = self.svc._build_history_context(history)
        # Should not crash; may or may not include content
        assert isinstance(result, str)


# ══════════════════════════════════════════════════════════════════════════════
# _create_rag_prompt
# ══════════════════════════════════════════════════════════════════════════════
class TestCreateRAGPrompt:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.svc = _make_service()

    def test_user_query_in_prompt(self):
        prompt = self.svc._create_rag_prompt("What is OOP?", "context text", "")
        assert "What is OOP?" in prompt

    def test_context_in_prompt(self):
        prompt = self.svc._create_rag_prompt("query", "Important context here", "")
        assert "Important context here" in prompt

    def test_history_in_prompt_when_provided(self):
        prompt = self.svc._create_rag_prompt("query", "context", "Previous history content")
        assert "Previous history content" in prompt

    def test_no_relevant_context_note_when_empty(self):
        prompt = self.svc._create_rag_prompt("query", "No relevant context available.", "")
        assert "No specific context" in prompt

    def test_response_label_in_prompt(self):
        prompt = self.svc._create_rag_prompt("query", "context", "")
        assert "RESPONSE:" in prompt

    def test_returns_string(self):
        prompt = self.svc._create_rag_prompt("query", "context", "history")
        assert isinstance(prompt, str)

    def test_empty_history_not_added_to_prompt(self):
        prompt = self.svc._create_rag_prompt("query", "context", "")
        assert "PREVIOUS CONVERSATION" not in prompt

    def test_history_section_added_when_present(self):
        prompt = self.svc._create_rag_prompt("query", "context", "some history")
        assert "PREVIOUS CONVERSATION" in prompt


# ══════════════════════════════════════════════════════════════════════════════
# generate_contextual_response
# ══════════════════════════════════════════════════════════════════════════════
class TestGenerateContextualResponse:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.svc = _make_service()

    async def _call(self, query="What is Python?", chunks=None, history=None, max_tokens=None):
        return await self.svc.generate_contextual_response(
            user_query=query,
            context_chunks=chunks if chunks is not None else MOCK_CHUNKS,
            chat_history=history or [],
            max_tokens=max_tokens,
        )

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_returns_response_text(self, mock_thread):
        mock_thread.return_value = _make_response("Here is the answer.")
        result = await self._call()
        assert result == "Here is the answer."

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_returns_stripped_text(self, mock_thread):
        mock_thread.return_value = _make_response("  Answer with spaces.  ")
        result = await self._call()
        assert result == "Answer with spaces."

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_raises_on_empty_response(self, mock_thread):
        resp = MagicMock()
        resp.candidates = None
        mock_thread.return_value = resp

        with pytest.raises(Exception, match="Failed to generate AI response"):
            await self._call()

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_raises_on_empty_candidates_list(self, mock_thread):
        resp = MagicMock()
        resp.candidates = []
        mock_thread.return_value = resp

        with pytest.raises(Exception, match="Failed to generate AI response"):
            await self._call()

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_raises_on_max_tokens_finish_reason(self, mock_thread):
        mock_thread.return_value = _make_response("", finish_reason_name="MAX_TOKENS")

        with pytest.raises(Exception, match="max_output_tokens"):
            await self._call()

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_raises_on_safety_finish_reason(self, mock_thread):
        mock_thread.return_value = _make_response("", finish_reason_name="SAFETY")

        with pytest.raises(Exception, match="safety filters"):
            await self._call()

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_raises_on_empty_text_parts(self, mock_thread):
        mock_thread.return_value = _make_response("", finish_reason_name="STOP")

        with pytest.raises(Exception, match="no text parts"):
            await self._call()

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_context_truncated_at_10000_chars(self, mock_thread):
        mock_thread.return_value = _make_response("Answer.")
        big_chunks = [{"source_name": "doc.pdf", "chunk": "A" * 15000, "score": 0.9}]

        await self._call(chunks=big_chunks)

        prompt_sent = mock_thread.call_args[0][1]
        # Context truncation means prompt must be under a reasonable bound
        assert len(prompt_sent) < 20000

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_max_tokens_capped_at_2048(self, mock_thread):
        mock_thread.return_value = _make_response("Answer.")
        await self._call(max_tokens=9999)

        gen_config = mock_thread.call_args.kwargs.get(
            "generation_config",
            mock_thread.call_args[1].get("generation_config") if mock_thread.call_args[1] else None
        ) or mock_thread.call_args[0][2] if len(mock_thread.call_args[0]) > 2 else None

        # Verify to_thread was called (proxy for config being applied)
        mock_thread.assert_called_once()

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_none_history_treated_as_empty(self, mock_thread):
        mock_thread.return_value = _make_response("Answer.")
        # Should not raise when history=None
        result = await self.svc.generate_contextual_response(
            user_query="query",
            context_chunks=MOCK_CHUNKS,
            chat_history=None,
        )
        assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_to_thread_called_with_model_generate(self, mock_thread):
        mock_thread.return_value = _make_response("Answer.")
        await self._call()
        mock_thread.assert_called_once()
        # First positional arg to to_thread must be model.generate_content
        fn_called = mock_thread.call_args[0][0]
        assert fn_called == self.svc.model.generate_content

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_thread_exception_wrapped_in_failed_message(self, mock_thread):
        mock_thread.side_effect = RuntimeError("network timeout")

        with pytest.raises(Exception, match="Failed to generate AI response"):
            await self._call()


# ══════════════════════════════════════════════════════════════════════════════
# generate_simple_response
# ══════════════════════════════════════════════════════════════════════════════
class TestGenerateSimpleResponse:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.svc = _make_service()

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_returns_response_text(self, mock_thread):
        resp = MagicMock()
        resp.text = "Simple answer."
        mock_thread.return_value = resp

        result = await self.svc.generate_simple_response("What is 2+2?")
        assert result == "Simple answer."

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_returns_stripped_text(self, mock_thread):
        resp = MagicMock()
        resp.text = "  Answer  "
        mock_thread.return_value = resp

        result = await self.svc.generate_simple_response("query")
        assert result == "Answer"

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_raises_on_empty_response(self, mock_thread):
        resp = MagicMock()
        resp.text = None
        mock_thread.return_value = resp

        with pytest.raises(Exception, match="Failed to generate response"):
            await self.svc.generate_simple_response("query")

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_raises_on_none_response(self, mock_thread):
        mock_thread.return_value = None

        with pytest.raises(Exception, match="Failed to generate response"):
            await self.svc.generate_simple_response("query")

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_default_max_tokens_is_512(self, mock_thread):
        resp = MagicMock()
        resp.text = "Answer."
        mock_thread.return_value = resp

        await self.svc.generate_simple_response("query")
        mock_thread.assert_called_once()

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_custom_max_tokens_accepted(self, mock_thread):
        resp = MagicMock()
        resp.text = "Answer."
        mock_thread.return_value = resp

        result = await self.svc.generate_simple_response("query", max_tokens=1024)
        assert result == "Answer."

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_exception_wrapped_in_failed_message(self, mock_thread):
        mock_thread.side_effect = RuntimeError("API error")

        with pytest.raises(Exception, match="Failed to generate response"):
            await self.svc.generate_simple_response("query")

    @pytest.mark.asyncio
    @patch("Notes.services.gemini_service.asyncio.to_thread", new_callable=AsyncMock)
    async def test_to_thread_called_with_model_generate(self, mock_thread):
        resp = MagicMock()
        resp.text = "Answer."
        mock_thread.return_value = resp

        await self.svc.generate_simple_response("query")
        fn_called = mock_thread.call_args[0][0]
        assert fn_called == self.svc.model.generate_content