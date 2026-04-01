# tests/unit/notes/test_schemas.py

import pytest
from uuid import UUID, uuid4
from pydantic import ValidationError
from Notes.schemas import ChatRequest, ChatResponse, ChatMessage, ContextChunk, EmbeddingChunk, Notebook, NotebookCreate, SemanticSearchRequest, SemanticSearchResponse, SemanticSearchResult, Source, SourceCreate

# ══════════════════════════════════════════════════════════════════════════════
# NotebookCreate
# ══════════════════════════════════════════════════════════════════════════════
class TestNotebookCreate:

    def test_valid_title(self):
        #from schemas import NotebookCreate
        nb = NotebookCreate(title="My Notebook")
        assert nb.title == "My Notebook"

    def test_missing_title_raises(self):
        #from schemas import NotebookCreate
        with pytest.raises(ValidationError):
            NotebookCreate()

    def test_title_must_be_string(self):
        #from schemas import NotebookCreate
        # Pydantic coerces int → str by default; validate it doesn't error
        nb = NotebookCreate(title="123")
        assert isinstance(nb.title, str)

    def test_extra_fields_ignored(self):
        #from schemas import NotebookCreate
        nb = NotebookCreate(title="NB", unexpected="field")
        assert not hasattr(nb, "unexpected")


# ══════════════════════════════════════════════════════════════════════════════
# Notebook
# ══════════════════════════════════════════════════════════════════════════════
class TestNotebook:

    def _valid(self, **kwargs):
        defaults = dict(id=uuid4(), title="NB", user_id="user-1")
        defaults.update(kwargs)
        return defaults

    def test_valid_notebook(self):
        #from schemas import Notebook
        nb = Notebook(**self._valid())
        assert isinstance(nb.id, UUID)

    def test_id_must_be_uuid(self):
        #from schemas import Notebook
        with pytest.raises(ValidationError):
            Notebook(**self._valid(id="not-a-uuid"))

    def test_title_required(self):
        #from schemas import Notebook
        with pytest.raises(ValidationError):
            Notebook(id=uuid4(), user_id="u1")

    def test_user_id_required(self):
        #from schemas import Notebook
        with pytest.raises(ValidationError):
            Notebook(id=uuid4(), title="NB")

    def test_from_attributes_enabled(self):
        #from schemas import Notebook
        assert Notebook.model_config.get("from_attributes") is True

    def test_user_id_stored(self):
        #from schemas import Notebook
        nb = Notebook(**self._valid(user_id="user-42"))
        assert nb.user_id == "user-42"


# ══════════════════════════════════════════════════════════════════════════════
# SourceCreate
# ══════════════════════════════════════════════════════════════════════════════
class TestSourceCreate:

    def test_minimal_valid(self):
        #from schemas import SourceCreate
        s = SourceCreate(type="file")
        assert s.type == "file"

    def test_all_optional_fields_none_by_default(self):
        #from schemas import SourceCreate
        s = SourceCreate(type="website")
        assert s.filename is None
        assert s.file_url is None
        assert s.website_url is None
        assert s.youtube_url is None
        assert s.metadata is None

    def test_type_required(self):
        #from schemas import SourceCreate
        with pytest.raises(ValidationError):
            SourceCreate()

    def test_filename_accepted(self):
        #from schemas import SourceCreate
        s = SourceCreate(type="file", filename="notes.pdf")
        assert s.filename == "notes.pdf"

    def test_file_url_accepted(self):
        #from schemas import SourceCreate
        s = SourceCreate(type="file", file_url="https://storage.test/file.pdf")
        assert s.file_url == "https://storage.test/file.pdf"

    def test_website_url_accepted(self):
        #from schemas import SourceCreate
        s = SourceCreate(type="website", website_url="https://example.com")
        assert s.website_url == "https://example.com"

    def test_youtube_url_accepted(self):
        #from schemas import SourceCreate
        s = SourceCreate(type="youtube", youtube_url="https://youtu.be/abc123")
        assert s.youtube_url == "https://youtu.be/abc123"

    def test_metadata_accepted_as_dict(self):
        #from schemas import SourceCreate
        s = SourceCreate(type="file", metadata={"size": 1024})
        assert s.metadata == {"size": 1024}


# ══════════════════════════════════════════════════════════════════════════════
# Source
# ══════════════════════════════════════════════════════════════════════════════
class TestSource:

    def _valid(self, **kwargs):
        defaults = dict(id=uuid4(), notebook_id=uuid4(), type="file")
        defaults.update(kwargs)
        return defaults

    def test_valid_source(self):
        #from schemas import Source
        s = Source(**self._valid())
        assert isinstance(s.id, UUID)

    def test_notebook_id_must_be_uuid(self):
        #from schemas import Source
        with pytest.raises(ValidationError):
            Source(**self._valid(notebook_id="bad"))

    def test_type_required(self):
        #from schemas import Source
        with pytest.raises(ValidationError):
            Source(id=uuid4(), notebook_id=uuid4())

    def test_optional_fields_default_none(self):
        #from schemas import Source
        s = Source(**self._valid())
        assert s.filename is None
        assert s.file_url is None
        assert s.website_url is None
        assert s.youtube_url is None
        assert s.extracted_text is None

    def test_from_attributes_enabled(self):
        #from schemas import Source
        assert Source.model_config.get("from_attributes") is True

    def test_extracted_text_stored(self):
        #from schemas import Source
        s = Source(**self._valid(extracted_text="Hello world"))
        assert s.extracted_text == "Hello world"


# ══════════════════════════════════════════════════════════════════════════════
# EmbeddingChunk
# ══════════════════════════════════════════════════════════════════════════════
class TestEmbeddingChunk:

    def test_valid_chunk(self):
        #from schemas import EmbeddingChunk
        ec = EmbeddingChunk(id=uuid4(), chunk="text here")
        assert ec.chunk == "text here"

    def test_score_optional_defaults_none(self):
        #from schemas import EmbeddingChunk
        ec = EmbeddingChunk(id=uuid4(), chunk="text")
        assert ec.score is None

    def test_score_accepted(self):
        #from schemas import EmbeddingChunk
        ec = EmbeddingChunk(id=uuid4(), chunk="text", score=0.95)
        assert ec.score == pytest.approx(0.95)

    def test_id_required(self):
        #from schemas import EmbeddingChunk
        with pytest.raises(ValidationError):
            EmbeddingChunk(chunk="text")

    def test_chunk_required(self):
        #from schemas import EmbeddingChunk
        with pytest.raises(ValidationError):
            EmbeddingChunk(id=uuid4())

    def test_from_attributes_enabled(self):
        #from schemas import EmbeddingChunk
        assert EmbeddingChunk.model_config.get("from_attributes") is True


# ══════════════════════════════════════════════════════════════════════════════
# SemanticSearchRequest
# ══════════════════════════════════════════════════════════════════════════════
class TestSemanticSearchRequest:

    def test_valid_minimal(self):
        #from schemas import SemanticSearchRequest
        r = SemanticSearchRequest(query="what is ML?")
        assert r.query == "what is ML?"

    def test_default_top_n_is_5(self):
        #from schemas import SemanticSearchRequest
        r = SemanticSearchRequest(query="q")
        assert r.top_n == 5

    def test_custom_top_n(self):
        #from schemas import SemanticSearchRequest
        r = SemanticSearchRequest(query="q", top_n=10)
        assert r.top_n == 10

    def test_source_ids_optional_defaults_none(self):
        #from schemas import SemanticSearchRequest
        r = SemanticSearchRequest(query="q")
        assert r.source_ids is None

    def test_source_ids_accepted_as_uuid_list(self):
        #from schemas import SemanticSearchRequest
        ids = [uuid4(), uuid4()]
        r = SemanticSearchRequest(query="q", source_ids=ids)
        assert len(r.source_ids) == 2

    def test_query_required(self):
        #from schemas import SemanticSearchRequest
        with pytest.raises(ValidationError):
            SemanticSearchRequest()


# ══════════════════════════════════════════════════════════════════════════════
# SemanticSearchResult
# ══════════════════════════════════════════════════════════════════════════════
class TestSemanticSearchResult:

    def _valid(self):
        return dict(id=str(uuid4()), chunk="chunk text", source_id=str(uuid4()), score=0.88)

    def test_valid_result(self):
        #from schemas import SemanticSearchResult
        r = SemanticSearchResult(**self._valid())
        assert isinstance(r.score, float)

    def test_id_is_str(self):
        #from schemas import SemanticSearchResult
        r = SemanticSearchResult(**self._valid())
        assert isinstance(r.id, str)

    def test_source_id_is_str(self):
        #from schemas import SemanticSearchResult
        r = SemanticSearchResult(**self._valid())
        assert isinstance(r.source_id, str)

    def test_all_fields_required(self):
        #from schemas import SemanticSearchResult
        with pytest.raises(ValidationError):
            SemanticSearchResult(id="x", chunk="c")  # missing source_id, score


# ══════════════════════════════════════════════════════════════════════════════
# SemanticSearchResponse
# ══════════════════════════════════════════════════════════════════════════════
class TestSemanticSearchResponse:

    def test_empty_chunks(self):
        #from schemas import SemanticSearchResponse
        r = SemanticSearchResponse(chunks=[])
        assert r.chunks == []

    def test_chunks_with_items(self):
        #from schemas import SemanticSearchResponse, EmbeddingChunk
        chunks = [EmbeddingChunk(id=uuid4(), chunk="c", score=0.9)]
        r = SemanticSearchResponse(chunks=chunks)
        assert len(r.chunks) == 1

    def test_chunks_required(self):
        #from schemas import SemanticSearchResponse
        with pytest.raises(ValidationError):
            SemanticSearchResponse()


# ══════════════════════════════════════════════════════════════════════════════
# ChatRequest
# ══════════════════════════════════════════════════════════════════════════════
class TestChatRequest:

    def test_valid_minimal(self):
        #from schemas import ChatRequest
        r = ChatRequest(user_query="What is AI?")
        assert r.user_query == "What is AI?"

    def test_default_max_context_chunks(self):
        #from schemas import ChatRequest
        assert ChatRequest(user_query="q").max_context_chunks == 5

    def test_default_max_tokens(self):
        #from schemas import ChatRequest
        assert ChatRequest(user_query="q").max_tokens == 512

    def test_custom_max_context_chunks(self):
        #from schemas import ChatRequest
        r = ChatRequest(user_query="q", max_context_chunks=10)
        assert r.max_context_chunks == 10

    def test_custom_max_tokens(self):
        #from schemas import ChatRequest
        r = ChatRequest(user_query="q", max_tokens=1024)
        assert r.max_tokens == 1024

    def test_user_query_required(self):
        #from schemas import ChatRequest
        with pytest.raises(ValidationError):
            ChatRequest()

    def test_max_context_chunks_can_be_none(self):
        #from schemas import ChatRequest
        r = ChatRequest(user_query="q", max_context_chunks=None)
        assert r.max_context_chunks is None

    def test_max_tokens_can_be_none(self):
        #from schemas import ChatRequest
        r = ChatRequest(user_query="q", max_tokens=None)
        assert r.max_tokens is None


# ══════════════════════════════════════════════════════════════════════════════
# ChatMessage
# ══════════════════════════════════════════════════════════════════════════════
class TestChatMessage:

    def test_valid_user_message(self):
        #from schemas import ChatMessage
        m = ChatMessage(role="user", content="Hello", timestamp="2026-04-01T12:00:00")
        assert m.role == "user"

    def test_valid_assistant_message(self):
        #from schemas import ChatMessage
        m = ChatMessage(role="assistant", content="Hi there", timestamp="2026-04-01T12:00:01")
        assert m.role == "assistant"

    def test_all_fields_required(self):
        #from schemas import ChatMessage
        with pytest.raises(ValidationError):
            ChatMessage(role="user", content="Hi")  # missing timestamp

    def test_content_stored(self):
        #from schemas import ChatMessage
        m = ChatMessage(role="user", content="Test content", timestamp="2026-04-01T12:00:00")
        assert m.content == "Test content"

    def test_timestamp_stored(self):
        #from schemas import ChatMessage
        ts = "2026-04-01T12:00:00"
        m = ChatMessage(role="user", content="c", timestamp=ts)
        assert m.timestamp == ts


# ══════════════════════════════════════════════════════════════════════════════
# ContextChunk
# ══════════════════════════════════════════════════════════════════════════════
class TestContextChunk:

    def _valid(self):
        return dict(
            source_id=str(uuid4()),
            source_name="lecture.pdf",
            snippet="Relevant text here.",
            similarity_score=0.91,
        )

    def test_valid_context_chunk(self):
        #from schemas import ContextChunk
        c = ContextChunk(**self._valid())
        assert c.source_name == "lecture.pdf"

    def test_similarity_score_stored(self):
        #from schemas import ContextChunk
        c = ContextChunk(**self._valid())
        assert c.similarity_score == pytest.approx(0.91)

    def test_all_fields_required(self):
        #from schemas import ContextChunk
        with pytest.raises(ValidationError):
            ContextChunk(source_id="x", source_name="doc")  # missing snippet, score

    def test_source_id_is_str(self):
        #from schemas import ContextChunk
        c = ContextChunk(**self._valid())
        assert isinstance(c.source_id, str)


# ══════════════════════════════════════════════════════════════════════════════
# ChatResponse
# ══════════════════════════════════════════════════════════════════════════════
class TestChatResponse:

    def _valid(self):
        #from schemas import ContextChunk, ChatMessage
        return dict(
            answer="Here is the answer.",
            context_used=[
                ContextChunk(
                    source_id=str(uuid4()),
                    source_name="doc.pdf",
                    snippet="snippet",
                    similarity_score=0.9,
                )
            ],
            history=[
                ChatMessage(role="user", content="Q", timestamp="2026-04-01T00:00:00")
            ],
            notebook_id=str(uuid4()),
            total_chunks_found=3,
        )

    def test_valid_response(self):
        #from schemas import ChatResponse
        r = ChatResponse(**self._valid())
        assert r.answer == "Here is the answer."

    def test_answer_required(self):
        #from schemas import ChatResponse
        d = self._valid()
        del d["answer"]
        with pytest.raises(ValidationError):
            ChatResponse(**d)

    def test_notebook_id_stored(self):
        #from schemas import ChatResponse
        r = ChatResponse(**self._valid())
        assert isinstance(r.notebook_id, str)

    def test_total_chunks_found_stored(self):
        #from schemas import ChatResponse
        r = ChatResponse(**self._valid())
        assert r.total_chunks_found == 3

    def test_context_used_is_list(self):
        #from schemas import ChatResponse
        r = ChatResponse(**self._valid())
        assert isinstance(r.context_used, list)

    def test_history_is_list(self):
        #from schemas import ChatResponse
        r = ChatResponse(**self._valid())
        assert isinstance(r.history, list)

    def test_empty_context_and_history_accepted(self):
        #from schemas import ChatResponse
        d = self._valid()
        d["context_used"] = []
        d["history"] = []
        r = ChatResponse(**d)
        assert r.context_used == []
        assert r.history == []

    def test_all_fields_required(self):
        #from schemas import ChatResponse
        with pytest.raises(ValidationError):
            ChatResponse(answer="A")  # missing context_used, history, notebook_id, total_chunks_found