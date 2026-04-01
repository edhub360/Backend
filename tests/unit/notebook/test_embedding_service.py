# tests/unit/notes/services/test_embedding_service.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4
from fastapi import HTTPException

SOURCE_ID = uuid4()
NOTEBOOK_ID = str(uuid4())
USER_ID = "user_abc"

MOCK_VECTOR = [0.1] * 768
LONG_TEXT = "word " * 600  # 600 words → 2 chunks at max_tokens=500


# ══════════════════════════════════════════════════════════════════════════════
# chunk_text
# ══════════════════════════════════════════════════════════════════════════════
class TestChunkText:

    def _call(self, text, max_tokens=500):
        from Notes.services.embedding_service import chunk_text
        return chunk_text(text, max_tokens)

    def test_empty_string_returns_empty_list(self):
        assert self._call("") == []

    def test_none_returns_empty_list(self):
        assert self._call(None) == []

    def test_whitespace_only_returns_empty_list(self):
        assert self._call("   ") == []

    def test_short_text_returns_single_chunk(self):
        result = self._call("hello world foo bar")
        assert len(result) == 1

    def test_long_text_splits_into_multiple_chunks(self):
        result = self._call(LONG_TEXT, max_tokens=500)
        assert len(result) == 2

    def test_chunk_size_respects_max_tokens(self):
        result = self._call(LONG_TEXT, max_tokens=500)
        for chunk in result:
            assert len(chunk.split()) <= 500

    def test_no_empty_chunks_in_output(self):
        result = self._call("a b c d e", max_tokens=2)
        assert all(len(c.strip()) > 0 for c in result)

    def test_exact_boundary_single_chunk(self):
        text = " ".join(["word"] * 500)
        result = self._call(text, max_tokens=500)
        assert len(result) == 1

    def test_custom_max_tokens(self):
        text = " ".join(["w"] * 100)
        result = self._call(text, max_tokens=10)
        assert len(result) == 10

    def test_all_words_preserved(self):
        words = [f"w{i}" for i in range(50)]
        text = " ".join(words)
        result = self._call(text, max_tokens=10)
        rejoined = " ".join(result)
        for word in words:
            assert word in rejoined


# ══════════════════════════════════════════════════════════════════════════════
# embed_text
# ══════════════════════════════════════════════════════════════════════════════
class TestEmbedText:

    @pytest.fixture(autouse=True)
    def patch_genai(self):
        with patch("services.embedding_service.genai") as mock_genai:
            self.mock_genai = mock_genai
            yield

    async def _call(self, text="hello world"):
        from Notes.services.embedding_service import embed_text
        return await embed_text(text)

    def _set_dict_response(self, vector=None):
        v = vector or MOCK_VECTOR
        self.mock_genai.embed_content.return_value = {"embedding": v}

    def _set_attr_response(self, vector=None):
        v = vector or MOCK_VECTOR
        result = MagicMock()
        result.embedding = v
        del result.embeddings
        self.mock_genai.embed_content.return_value = result

    def _set_dict_embeddings_response(self, vector=None):
        v = vector or MOCK_VECTOR
        self.mock_genai.embed_content.return_value = {"embeddings": [{"values": v}]}

    @pytest.mark.asyncio
    async def test_dict_response_returns_vector(self):
        self._set_dict_response()
        result = await self._call()
        assert result == MOCK_VECTOR

    @pytest.mark.asyncio
    async def test_attr_response_returns_vector(self):
        self._set_attr_response()
        result = await self._call()
        assert result == MOCK_VECTOR

    @pytest.mark.asyncio
    async def test_dict_embeddings_response_returns_vector(self):
        self._set_dict_embeddings_response()
        result = await self._call()
        assert result == MOCK_VECTOR

    @pytest.mark.asyncio
    async def test_missing_embedding_raises_http_500(self):
        self.mock_genai.embed_content.return_value = {}
        with pytest.raises(HTTPException) as exc:
            await self._call()
        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_genai_exception_raises_http_500(self):
        self.mock_genai.embed_content.side_effect = RuntimeError("API down")
        with pytest.raises(HTTPException) as exc:
            await self._call()
        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_embed_content_called_with_correct_model(self):
        self._set_dict_response()
        await self._call("test text")
        call_kwargs = self.mock_genai.embed_content.call_args.kwargs
        assert call_kwargs["model"] == "models/gemini-embedding-001"

    @pytest.mark.asyncio
    async def test_embed_content_called_with_correct_dimensionality(self):
        self._set_dict_response()
        await self._call("test text")
        call_kwargs = self.mock_genai.embed_content.call_args.kwargs
        assert call_kwargs["output_dimensionality"] == 768


# ══════════════════════════════════════════════════════════════════════════════
# embed_texts_batch
# ══════════════════════════════════════════════════════════════════════════════
class TestEmbedTextsBatch:

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_returns_vector_per_text(self, mock_embed):
        mock_embed.return_value = MOCK_VECTOR
        from Notes.services.embedding_service import embed_texts_batch
        result = await embed_texts_batch(["a", "b", "c"])
        assert len(result) == 3

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_empty_input_returns_empty_list(self, mock_embed):
        from Notes.services.embedding_service import embed_texts_batch
        result = await embed_texts_batch([])
        assert result == []

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_empty_strings_skipped(self, mock_embed):
        mock_embed.return_value = MOCK_VECTOR
        from Notes.services.embedding_service import embed_texts_batch
        result = await embed_texts_batch(["valid text", "", "   ", "another valid"])
        assert len(result) == 2

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_embed_text_called_for_each_valid_text(self, mock_embed):
        mock_embed.return_value = MOCK_VECTOR
        from Notes.services.embedding_service import embed_texts_batch
        await embed_texts_batch(["a", "b"])
        assert mock_embed.call_count == 2

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_embed_text_exception_raises_http_500(self, mock_embed):
        mock_embed.side_effect = HTTPException(status_code=500, detail="API error")
        from Notes.services.embedding_service import embed_texts_batch
        with pytest.raises(HTTPException) as exc:
            await embed_texts_batch(["text1", "text2"])
        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    @patch("services.embedding_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_sleep_called_every_10_items(self, mock_embed, mock_sleep):
        mock_embed.return_value = MOCK_VECTOR
        from Notes.services.embedding_service import embed_texts_batch
        texts = [f"text {i}" for i in range(15)]
        await embed_texts_batch(texts)
        mock_sleep.assert_called()


# ══════════════════════════════════════════════════════════════════════════════
# store_embeddings_for_source
# ══════════════════════════════════════════════════════════════════════════════
class TestStoreEmbeddingsForSource:

    def _make_source(self, text="word " * 100):
        src = MagicMock()
        src.id = SOURCE_ID
        src.extracted_text = text
        return src

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_texts_batch", new_callable=AsyncMock)
    @patch("services.embedding_service.chunk_text")
    async def test_returns_embeddings_list(self, mock_chunk, mock_batch):
        mock_chunk.return_value = ["chunk1", "chunk2"]
        mock_batch.return_value = [MOCK_VECTOR, MOCK_VECTOR]

        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()

        with patch("services.embedding_service.Embedding") as MockEmb:
            emb1, emb2 = MagicMock(), MagicMock()
            MockEmb.side_effect = [emb1, emb2]

            from Notes.services.embedding_service import store_embeddings_for_source
            result = await store_embeddings_for_source(self._make_source(), session)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_empty_text_returns_empty_list(self):
        from Notes.services.embedding_service import store_embeddings_for_source
        session = AsyncMock()
        result = await store_embeddings_for_source(self._make_source(""), session)
        assert result == []

    @pytest.mark.asyncio
    async def test_short_text_returns_empty_list(self):
        from Notes.services.embedding_service import store_embeddings_for_source
        session = AsyncMock()
        result = await store_embeddings_for_source(self._make_source("hi"), session)
        assert result == []

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_texts_batch", new_callable=AsyncMock)
    @patch("services.embedding_service.chunk_text")
    async def test_session_add_called_per_embedding(self, mock_chunk, mock_batch):
        mock_chunk.return_value = ["chunk1", "chunk2"]
        mock_batch.return_value = [MOCK_VECTOR, MOCK_VECTOR]

        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()

        with patch("services.embedding_service.Embedding"):
            from Notes.services.embedding_service import store_embeddings_for_source
            await store_embeddings_for_source(self._make_source(), session)

        assert session.add.call_count == 2

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_texts_batch", new_callable=AsyncMock)
    @patch("services.embedding_service.chunk_text")
    async def test_session_commit_called(self, mock_chunk, mock_batch):
        mock_chunk.return_value = ["chunk1"]
        mock_batch.return_value = [MOCK_VECTOR]

        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()

        with patch("services.embedding_service.Embedding"):
            from Notes.services.embedding_service import store_embeddings_for_source
            await store_embeddings_for_source(self._make_source(), session)

        session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_texts_batch", new_callable=AsyncMock)
    @patch("services.embedding_service.chunk_text")
    async def test_chunk_vector_mismatch_returns_empty_list(self, mock_chunk, mock_batch):
        mock_chunk.return_value = ["chunk1", "chunk2"]
        mock_batch.return_value = [MOCK_VECTOR]  # only 1 vector for 2 chunks

        session = AsyncMock()
        from Notes.services.embedding_service import store_embeddings_for_source
        result = await store_embeddings_for_source(self._make_source(), session)
        assert result == []

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_texts_batch", new_callable=AsyncMock)
    @patch("services.embedding_service.chunk_text")
    async def test_exception_triggers_rollback(self, mock_chunk, mock_batch):
        mock_chunk.return_value = ["chunk1"]
        mock_batch.side_effect = RuntimeError("embed failed")

        session = AsyncMock()
        session.rollback = AsyncMock()

        from Notes.services.embedding_service import store_embeddings_for_source
        with pytest.raises(HTTPException):
            await store_embeddings_for_source(self._make_source(), session)

        session.rollback.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.embedding_service.chunk_text")
    async def test_no_chunks_returns_empty_list(self, mock_chunk):
        mock_chunk.return_value = []
        from Notes.services.embedding_service import store_embeddings_for_source
        result = await store_embeddings_for_source(self._make_source(), AsyncMock())
        assert result == []


# ══════════════════════════════════════════════════════════════════════════════
# semantic_search
# ══════════════════════════════════════════════════════════════════════════════
class TestSemanticSearch:

    def _make_request(self, query="test query", top_n=5, source_ids=None):
        from Notes.schemas import SemanticSearchRequest
        return SemanticSearchRequest(query=query, top_n=top_n, source_ids=source_ids)

    def _make_rows(self, n=2):
        rows = []
        for _ in range(n):
            row = MagicMock()
            row.id = uuid4()
            row.chunk = "Some relevant chunk text"
            row.source_id = uuid4()
            row.similarity_score = 0.91
            rows.append(row)
        return rows

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_returns_chunks_key(self, mock_embed):
        mock_embed.return_value = MOCK_VECTOR
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = self._make_rows(2)
        session.execute = AsyncMock(return_value=result_mock)

        from Notes.services.embedding_service import semantic_search
        result = await semantic_search(self._make_request(), session)
        assert "chunks" in result

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_returns_correct_chunk_count(self, mock_embed):
        mock_embed.return_value = MOCK_VECTOR
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = self._make_rows(3)
        session.execute = AsyncMock(return_value=result_mock)

        from Notes.services.embedding_service import semantic_search
        result = await semantic_search(self._make_request(), session)
        assert len(result["chunks"]) == 3

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_chunk_has_required_keys(self, mock_embed):
        mock_embed.return_value = MOCK_VECTOR
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = self._make_rows(1)
        session.execute = AsyncMock(return_value=result_mock)

        from Notes.services.embedding_service import semantic_search
        result = await semantic_search(self._make_request(), session)
        chunk = result["chunks"][0]
        assert all(k in chunk for k in ("id", "chunk", "source_id", "score"))

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_empty_result_returns_empty_chunks(self, mock_embed):
        mock_embed.return_value = MOCK_VECTOR
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        from Notes.services.embedding_service import semantic_search
        result = await semantic_search(self._make_request(), session)
        assert result["chunks"] == []

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_embed_exception_raises_http_500(self, mock_embed):
        mock_embed.side_effect = HTTPException(status_code=500, detail="fail")
        session = AsyncMock()

        from Notes.services.embedding_service import semantic_search
        with pytest.raises(HTTPException) as exc:
            await semantic_search(self._make_request(), session)
        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_score_rounded_to_4_decimals(self, mock_embed):
        mock_embed.return_value = MOCK_VECTOR
        session = AsyncMock()
        row = MagicMock()
        row.id = uuid4()
        row.chunk = "text"
        row.source_id = uuid4()
        row.similarity_score = 0.912345678
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [row]
        session.execute = AsyncMock(return_value=result_mock)

        from Notes.services.embedding_service import semantic_search
        result = await semantic_search(self._make_request(), session)
        assert result["chunks"][0]["score"] == round(0.912345678, 4)


# ══════════════════════════════════════════════════════════════════════════════
# get_relevant_chunks_for_notebook
# ══════════════════════════════════════════════════════════════════════════════
class TestGetRelevantChunksForNotebook:

    def _make_rows(self, n=2):
        rows = []
        for _ in range(n):
            row = MagicMock()
            row.id = uuid4()
            row.chunk = "Relevant chunk content."
            row.source_id = uuid4()
            row.source_name = "lecture.pdf"
            row.source_type = "file"
            row.similarity_score = 0.88
            rows.append(row)
        return rows

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_returns_list_of_chunks(self, mock_embed):
        mock_embed.return_value = MOCK_VECTOR
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = self._make_rows(2)
        session.execute = AsyncMock(return_value=result_mock)

        from Notes.services.embedding_service import get_relevant_chunks_for_notebook
        result = await get_relevant_chunks_for_notebook(
            session, NOTEBOOK_ID, "what is python", top_n=5
        )
        assert len(result) == 2

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_chunk_has_source_name(self, mock_embed):
        mock_embed.return_value = MOCK_VECTOR
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = self._make_rows(1)
        session.execute = AsyncMock(return_value=result_mock)

        from Notes.services.embedding_service import get_relevant_chunks_for_notebook
        result = await get_relevant_chunks_for_notebook(
            session, NOTEBOOK_ID, "query"
        )
        assert "source_name" in result[0]

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_chunk_has_all_required_keys(self, mock_embed):
        mock_embed.return_value = MOCK_VECTOR
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = self._make_rows(1)
        session.execute = AsyncMock(return_value=result_mock)

        from Notes.services.embedding_service import get_relevant_chunks_for_notebook
        result = await get_relevant_chunks_for_notebook(
            session, NOTEBOOK_ID, "query"
        )
        assert all(k in result[0] for k in ("id", "chunk", "source_id", "source_name", "source_type", "score"))

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_with_user_id_executes_user_filtered_query(self, mock_embed):
        mock_embed.return_value = MOCK_VECTOR
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        from Notes.services.embedding_service import get_relevant_chunks_for_notebook
        await get_relevant_chunks_for_notebook(
            session, NOTEBOOK_ID, "query", user_id=USER_ID
        )
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_without_user_id_executes_simple_query(self, mock_embed):
        mock_embed.return_value = MOCK_VECTOR
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        from Notes.services.embedding_service import get_relevant_chunks_for_notebook
        await get_relevant_chunks_for_notebook(
            session, NOTEBOOK_ID, "query"
        )
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_null_source_name_defaults_to_unknown(self, mock_embed):
        mock_embed.return_value = MOCK_VECTOR
        session = AsyncMock()
        row = MagicMock()
        row.id = uuid4()
        row.chunk = "chunk"
        row.source_id = uuid4()
        row.source_name = None
        row.source_type = None
        row.similarity_score = 0.75
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [row]
        session.execute = AsyncMock(return_value=result_mock)

        from Notes.services.embedding_service import get_relevant_chunks_for_notebook
        result = await get_relevant_chunks_for_notebook(session, NOTEBOOK_ID, "query")
        assert result[0]["source_name"] == "Unknown"
        assert result[0]["source_type"] == "file"

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_embed_exception_raises_http_500(self, mock_embed):
        mock_embed.side_effect = HTTPException(status_code=500, detail="fail")
        session = AsyncMock()

        from Notes.services.embedding_service import get_relevant_chunks_for_notebook
        with pytest.raises(HTTPException) as exc:
            await get_relevant_chunks_for_notebook(session, NOTEBOOK_ID, "query")
        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    @patch("services.embedding_service.embed_text", new_callable=AsyncMock)
    async def test_score_rounded_to_4_decimals(self, mock_embed):
        mock_embed.return_value = MOCK_VECTOR
        row = MagicMock()
        row.id = uuid4()
        row.chunk = "chunk"
        row.source_id = uuid4()
        row.source_name = "doc.pdf"
        row.source_type = "file"
        row.similarity_score = 0.876543219
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [row]
        session = AsyncMock()
        session.execute = AsyncMock(return_value=result_mock)

        from Notes.services.embedding_service import get_relevant_chunks_for_notebook
        result = await get_relevant_chunks_for_notebook(session, NOTEBOOK_ID, "query")
        assert result[0]["score"] == round(0.876543219, 4)


# ══════════════════════════════════════════════════════════════════════════════
# get_embedding_stats
# ══════════════════════════════════════════════════════════════════════════════
class TestGetEmbeddingStats:

    @pytest.mark.asyncio
    async def test_returns_all_stat_keys(self):
        row = MagicMock()
        row.total_embeddings = 100
        row.unique_sources = 10
        row.avg_chunk_length = 245.7
        row.max_chunk_length = 500
        row.min_chunk_length = 50

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchone.return_value = row
        session.execute = AsyncMock(return_value=result_mock)

        from Notes.services.embedding_service import get_embedding_stats
        result = await get_embedding_stats(session)
        assert all(k in result for k in (
            "total_embeddings", "unique_sources",
            "avg_chunk_length", "max_chunk_length", "min_chunk_length"
        ))

    @pytest.mark.asyncio
    async def test_null_values_default_to_zero(self):
        row = MagicMock()
        row.total_embeddings = None
        row.unique_sources = None
        row.avg_chunk_length = None
        row.max_chunk_length = None
        row.min_chunk_length = None

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchone.return_value = row
        session.execute = AsyncMock(return_value=result_mock)

        from Notes.services.embedding_service import get_embedding_stats
        result = await get_embedding_stats(session)
        assert result["total_embeddings"] == 0
        assert result["unique_sources"] == 0

    @pytest.mark.asyncio
    async def test_avg_rounded_to_2_decimals(self):
        row = MagicMock()
        row.total_embeddings = 5
        row.unique_sources = 2
        row.avg_chunk_length = 123.456789
        row.max_chunk_length = 300
        row.min_chunk_length = 50

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchone.return_value = row
        session.execute = AsyncMock(return_value=result_mock)

        from Notes.services.embedding_service import get_embedding_stats
        result = await get_embedding_stats(session)
        assert result["avg_chunk_length"] == round(123.456789, 2)

    @pytest.mark.asyncio
    async def test_exception_raises_http_500(self):
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=RuntimeError("DB error"))

        from Notes.services.embedding_service import get_embedding_stats
        with pytest.raises(HTTPException) as exc:
            await get_embedding_stats(session)
        assert exc.value.status_code == 500


# ══════════════════════════════════════════════════════════════════════════════
# semantic_search_legacy
# ══════════════════════════════════════════════════════════════════════════════
class TestSemanticSearchLegacy:

    @pytest.mark.asyncio
    @patch("services.embedding_service.semantic_search", new_callable=AsyncMock)
    async def test_returns_chunks_list(self, mock_search):
        mock_search.return_value = {"chunks": [{"id": "1", "chunk": "text"}]}
        session = AsyncMock()

        from Notes.services.embedding_service import semantic_search_legacy
        result = await semantic_search_legacy("query", top_n=3, session=session)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    @patch("services.embedding_service.semantic_search", new_callable=AsyncMock)
    async def test_delegates_to_semantic_search(self, mock_search):
        mock_search.return_value = {"chunks": []}
        session = AsyncMock()

        from Notes.services.embedding_service import semantic_search_legacy
        await semantic_search_legacy("query", top_n=5, session=session)
        mock_search.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.embedding_service.semantic_search", new_callable=AsyncMock)
    async def test_propagates_exception(self, mock_search):
        mock_search.side_effect = HTTPException(status_code=500, detail="fail")
        session = AsyncMock()

        from Notes.services.embedding_service import semantic_search_legacy
        with pytest.raises(HTTPException):
            await semantic_search_legacy("query", session=session)