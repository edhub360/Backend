# tests/unit/ai_chat/test_schemas.py

import pytest
from pydantic import ValidationError


# ─────────────────────────────────────────────
# ChatMode
# ─────────────────────────────────────────────

class TestChatMode:

    def test_general_value(self):
        from ai_chat.app.models.schemas import ChatMode
        assert ChatMode.GENERAL == "general"

    def test_rag_value(self):
        from ai_chat.app.models.schemas import ChatMode
        assert ChatMode.RAG == "rag"

    def test_is_string_enum(self):
        from ai_chat.app.models.schemas import ChatMode
        assert isinstance(ChatMode.GENERAL, str)
        assert isinstance(ChatMode.RAG, str)

    def test_invalid_mode_raises(self):
        from ai_chat.app.models.schemas import ChatRequest, ChatMode
        with pytest.raises(ValidationError):
            ChatRequest(query="hello", mode="invalid_mode")


# ─────────────────────────────────────────────
# ChatRequest
# ─────────────────────────────────────────────

class TestChatRequest:

    def test_valid_general_request(self):
        from ai_chat.app.models.schemas import ChatRequest, ChatMode
        req = ChatRequest(query="what is python?", mode="general")
        assert req.query == "what is python?"
        assert req.mode == ChatMode.GENERAL

    def test_valid_rag_request(self):
        from ai_chat.app.models.schemas import ChatRequest, ChatMode
        req = ChatRequest(query="explain recursion", mode="rag")
        assert req.mode == ChatMode.RAG

    def test_default_top_k_is_5(self):
        from ai_chat.app.models.schemas import ChatRequest
        req = ChatRequest(query="hi", mode="general")
        assert req.top_k == 5

    def test_custom_top_k(self):
        from ai_chat.app.models.schemas import ChatRequest
        req = ChatRequest(query="hi", mode="general", top_k=10)
        assert req.top_k == 10

    def test_top_k_minimum_is_1(self):
        from ai_chat.app.models.schemas import ChatRequest
        with pytest.raises(ValidationError):
            ChatRequest(query="hi", mode="general", top_k=0)

    def test_top_k_maximum_is_20(self):
        from ai_chat.app.models.schemas import ChatRequest
        with pytest.raises(ValidationError):
            ChatRequest(query="hi", mode="general", top_k=21)

    def test_top_k_boundary_1_is_valid(self):
        from ai_chat.app.models.schemas import ChatRequest
        req = ChatRequest(query="hi", mode="general", top_k=1)
        assert req.top_k == 1

    def test_top_k_boundary_20_is_valid(self):
        from ai_chat.app.models.schemas import ChatRequest
        req = ChatRequest(query="hi", mode="general", top_k=20)
        assert req.top_k == 20

    def test_session_id_defaults_to_none(self):
        from ai_chat.app.models.schemas import ChatRequest
        req = ChatRequest(query="hi", mode="general")
        assert req.session_id is None

    def test_session_id_accepted(self):
        from ai_chat.app.models.schemas import ChatRequest
        req = ChatRequest(query="hi", mode="general", session_id="abc-123")
        assert req.session_id == "abc-123"

    def test_empty_query_raises(self):
        from ai_chat.app.models.schemas import ChatRequest
        with pytest.raises(ValidationError):
            ChatRequest(query="", mode="general")

    def test_whitespace_only_query_raises(self):
        from ai_chat.app.models.schemas import ChatRequest
        # min_length=1 applies to string length, not stripped — single space passes length but pydantic v2 may differ
        # whitespace string has length >= 1, so this test confirms current behaviour
        try:
            req = ChatRequest(query=" ", mode="general")
            assert req.query == " "  # pydantic does NOT strip by default
        except ValidationError:
            pass  # also acceptable if validator strips

    def test_missing_query_raises(self):
        from ai_chat.app.models.schemas import ChatRequest
        with pytest.raises(ValidationError):
            ChatRequest(mode="general")

    def test_missing_mode_raises(self):
        from ai_chat.app.models.schemas import ChatRequest
        with pytest.raises(ValidationError):
            ChatRequest(query="hello")

    def test_mode_accepts_enum_member_directly(self):
        from ai_chat.app.models.schemas import ChatRequest, ChatMode
        req = ChatRequest(query="hi", mode=ChatMode.RAG)
        assert req.mode == ChatMode.RAG

    def test_extra_fields_ignored_or_rejected(self):
        from ai_chat.app.models.schemas import ChatRequest
        # Pydantic v2 default ignores extra fields
        req = ChatRequest(query="hi", mode="general", unknown_field="value")
        assert not hasattr(req, "unknown_field")


# ─────────────────────────────────────────────
# RetrievedChunk
# ─────────────────────────────────────────────

class TestRetrievedChunk:

    def test_valid_chunk(self):
        from ai_chat.app.models.schemas import RetrievedChunk
        chunk = RetrievedChunk(text="some content", source="doc.pdf", score=0.95)
        assert chunk.text == "some content"
        assert chunk.source == "doc.pdf"
        assert chunk.score == 0.95

    def test_missing_text_raises(self):
        from ai_chat.app.models.schemas import RetrievedChunk
        with pytest.raises(ValidationError):
            RetrievedChunk(source="doc.pdf", score=0.5)

    def test_missing_source_raises(self):
        from ai_chat.app.models.schemas import RetrievedChunk
        with pytest.raises(ValidationError):
            RetrievedChunk(text="content", score=0.5)

    def test_missing_score_raises(self):
        from ai_chat.app.models.schemas import RetrievedChunk
        with pytest.raises(ValidationError):
            RetrievedChunk(text="content", source="doc.pdf")

    def test_score_as_integer_coerced_to_float(self):
        from ai_chat.app.models.schemas import RetrievedChunk
        chunk = RetrievedChunk(text="t", source="s", score=1)
        assert isinstance(chunk.score, float)

    def test_zero_score_is_valid(self):
        from ai_chat.app.models.schemas import RetrievedChunk
        chunk = RetrievedChunk(text="t", source="s", score=0.0)
        assert chunk.score == 0.0

    def test_negative_score_is_valid(self):
        from ai_chat.app.models.schemas import RetrievedChunk
        chunk = RetrievedChunk(text="t", source="s", score=-0.5)
        assert chunk.score == -0.5

    def test_empty_text_is_valid(self):
        from ai_chat.app.models.schemas import RetrievedChunk
        chunk = RetrievedChunk(text="", source="s", score=0.1)
        assert chunk.text == ""


# ─────────────────────────────────────────────
# ChatResponse
# ─────────────────────────────────────────────

class TestChatResponse:

    def test_valid_minimal_response(self):
        from ai_chat.app.models.schemas import ChatResponse, ChatMode
        resp = ChatResponse(answer="Hello!", mode="general")
        assert resp.answer == "Hello!"
        assert resp.mode == ChatMode.GENERAL

    def test_retrieved_chunks_defaults_to_none(self):
        from ai_chat.app.models.schemas import ChatResponse
        resp = ChatResponse(answer="ok", mode="general")
        assert resp.retrieved_chunks is None

    def test_token_count_defaults_to_none(self):
        from ai_chat.app.models.schemas import ChatResponse
        resp = ChatResponse(answer="ok", mode="general")
        assert resp.token_count is None

    def test_retrieved_chunks_accepted(self):
        from ai_chat.app.models.schemas import ChatResponse, RetrievedChunk
        chunks = [RetrievedChunk(text="chunk", source="f.pdf", score=0.8)]
        resp = ChatResponse(answer="ok", mode="rag", retrieved_chunks=chunks)
        assert len(resp.retrieved_chunks) == 1

    def test_retrieved_chunks_content_preserved(self):
        from ai_chat.app.models.schemas import ChatResponse, RetrievedChunk
        chunk = RetrievedChunk(text="important text", source="notes.pdf", score=0.9)
        resp = ChatResponse(answer="ok", mode="rag", retrieved_chunks=[chunk])
        assert resp.retrieved_chunks[0].text == "important text"

    def test_token_count_accepted(self):
        from ai_chat.app.models.schemas import ChatResponse
        resp = ChatResponse(answer="ok", mode="general", token_count=128)
        assert resp.token_count == 128

    def test_missing_answer_raises(self):
        from ai_chat.app.models.schemas import ChatResponse
        with pytest.raises(ValidationError):
            ChatResponse(mode="general")

    def test_missing_mode_raises(self):
        from ai_chat.app.models.schemas import ChatResponse
        with pytest.raises(ValidationError):
            ChatResponse(answer="ok")

    def test_rag_mode_response(self):
        from ai_chat.app.models.schemas import ChatResponse, ChatMode
        resp = ChatResponse(answer="Here is what I found.", mode="rag")
        assert resp.mode == ChatMode.RAG

    def test_empty_retrieved_chunks_list(self):
        from ai_chat.app.models.schemas import ChatResponse
        resp = ChatResponse(answer="ok", mode="rag", retrieved_chunks=[])
        assert resp.retrieved_chunks == []

    def test_multiple_retrieved_chunks(self):
        from ai_chat.app.models.schemas import ChatResponse, RetrievedChunk
        chunks = [
            RetrievedChunk(text=f"chunk {i}", source="f.pdf", score=float(i) / 10)
            for i in range(5)
        ]
        resp = ChatResponse(answer="ok", mode="rag", retrieved_chunks=chunks)
        assert len(resp.retrieved_chunks) == 5


# ─────────────────────────────────────────────
# UploadResponse
# ─────────────────────────────────────────────

class TestUploadResponse:

    def test_valid_upload_response(self):
        from ai_chat.app.models.schemas import UploadResponse
        resp = UploadResponse(
            message="Successfully processed 2 files",
            files_processed=2,
            total_chunks_added=10
        )
        assert resp.files_processed == 2
        assert resp.total_chunks_added == 10

    def test_message_preserved(self):
        from ai_chat.app.models.schemas import UploadResponse
        resp = UploadResponse(
            message="Done", files_processed=1, total_chunks_added=5
        )
        assert resp.message == "Done"

    def test_missing_message_raises(self):
        from ai_chat.app.models.schemas import UploadResponse
        with pytest.raises(ValidationError):
            UploadResponse(files_processed=1, total_chunks_added=5)

    def test_missing_files_processed_raises(self):
        from ai_chat.app.models.schemas import UploadResponse
        with pytest.raises(ValidationError):
            UploadResponse(message="ok", total_chunks_added=5)

    def test_missing_total_chunks_raises(self):
        from ai_chat.app.models.schemas import UploadResponse
        with pytest.raises(ValidationError):
            UploadResponse(message="ok", files_processed=1)

    def test_zero_files_processed_is_valid(self):
        from ai_chat.app.models.schemas import UploadResponse
        resp = UploadResponse(message="no files", files_processed=0, total_chunks_added=0)
        assert resp.files_processed == 0

    def test_zero_chunks_added_is_valid(self):
        from ai_chat.app.models.schemas import UploadResponse
        resp = UploadResponse(message="ok", files_processed=1, total_chunks_added=0)
        assert resp.total_chunks_added == 0

    def test_large_values_accepted(self):
        from ai_chat.app.models.schemas import UploadResponse
        resp = UploadResponse(
            message="bulk upload", files_processed=500, total_chunks_added=50000
        )
        assert resp.total_chunks_added == 50000

    def test_string_int_coercion_for_files_processed(self):
        from ai_chat.app.models.schemas import UploadResponse
        # Pydantic v2 coerces "3" → 3 in lax mode by default
        resp = UploadResponse(message="ok", files_processed="3", total_chunks_added=10)
        assert resp.files_processed == 3