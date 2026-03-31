# tests/unit/ai_chat/test_embeddings.py

import pytest
import numpy as np
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_embedding(dim: int = 768) -> list:
    return list(np.random.rand(dim).astype(np.float32))


def make_embed_result(dim: int = 768) -> dict:
    return {"embedding": make_embedding(dim)}


# ─────────────────────────────────────────────
# embed_texts
# ─────────────────────────────────────────────

class TestEmbedTexts:

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_returns_ndarray(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_texts

        mock_embed.return_value = make_embed_result()
        result = embed_texts(["hello world"])

        assert isinstance(result, np.ndarray)

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_single_text_shape(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_texts

        mock_embed.return_value = make_embed_result(dim=768)
        result = embed_texts(["single text"])

        assert result.shape == (1, 768)

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_multiple_texts_shape(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_texts

        mock_embed.return_value = make_embed_result(dim=768)
        result = embed_texts(["text one", "text two", "text three"])

        assert result.shape == (3, 768)

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_dtype_is_float32(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_texts

        mock_embed.return_value = make_embed_result()
        result = embed_texts(["test"])

        assert result.dtype == np.float32

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_empty_list_returns_empty_array(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_texts

        result = embed_texts([])

        mock_embed.assert_not_called()
        assert isinstance(result, np.ndarray)
        assert result.size == 0

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_calls_embed_content_once_per_text(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_texts

        mock_embed.return_value = make_embed_result()
        embed_texts(["a", "b", "c"])

        assert mock_embed.call_count == 3

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_uses_retrieval_document_task_type(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_texts

        mock_embed.return_value = make_embed_result()
        embed_texts(["some text"])

        _, kwargs = mock_embed.call_args
        assert kwargs.get("task_type") == "retrieval_document"

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_uses_default_model(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_texts

        mock_embed.return_value = make_embed_result()
        embed_texts(["text"])

        _, kwargs = mock_embed.call_args
        assert kwargs.get("model") == "models/text-embedding-004"

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_uses_custom_model(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_texts

        mock_embed.return_value = make_embed_result()
        embed_texts(["text"], model="models/custom-embed-v1")

        _, kwargs = mock_embed.call_args
        assert kwargs.get("model") == "models/custom-embed-v1"

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_passes_text_as_content(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_texts

        mock_embed.return_value = make_embed_result()
        embed_texts(["my document text"])

        _, kwargs = mock_embed.call_args
        assert kwargs.get("content") == "my document text"

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_embedding_values_match_mock(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_texts

        fixed = [0.1, 0.2, 0.3]
        mock_embed.return_value = {"embedding": fixed}
        result = embed_texts(["text"])

        np.testing.assert_array_almost_equal(result[0], fixed)

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_api_error_raises_runtime_error(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_texts

        mock_embed.side_effect = Exception("API quota exceeded")

        with pytest.raises(RuntimeError) as exc_info:
            embed_texts(["text"])

        assert "Error generating embeddings" in str(exc_info.value)
        assert "API quota exceeded" in str(exc_info.value)

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_api_error_message_wraps_original(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_texts

        mock_embed.side_effect = ConnectionError("network failure")

        with pytest.raises(RuntimeError) as exc_info:
            embed_texts(["text"])

        assert "network failure" in str(exc_info.value)

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_each_text_embedded_separately(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_texts

        calls_received = []

        def capture(**kwargs):
            calls_received.append(kwargs["content"])
            return make_embed_result(dim=4)

        mock_embed.side_effect = capture
        embed_texts(["first", "second", "third"])

        assert calls_received == ["first", "second", "third"]


# ─────────────────────────────────────────────
# embed_query
# ─────────────────────────────────────────────

class TestEmbedQuery:

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_returns_ndarray(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_query

        mock_embed.return_value = make_embed_result()
        result = embed_query("what is machine learning?")

        assert isinstance(result, np.ndarray)

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_output_shape_is_1_x_dim(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_query

        mock_embed.return_value = make_embed_result(dim=768)
        result = embed_query("test query")

        assert result.shape == (1, 768)

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_dtype_is_float32(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_query

        mock_embed.return_value = make_embed_result()
        result = embed_query("query")

        assert result.dtype == np.float32

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_uses_retrieval_query_task_type(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_query

        mock_embed.return_value = make_embed_result()
        embed_query("some question")

        _, kwargs = mock_embed.call_args
        assert kwargs.get("task_type") == "retrieval_query"

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_uses_default_model(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_query

        mock_embed.return_value = make_embed_result()
        embed_query("query")

        _, kwargs = mock_embed.call_args
        assert kwargs.get("model") == "models/text-embedding-004"

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_uses_custom_model(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_query

        mock_embed.return_value = make_embed_result()
        embed_query("query", model="models/custom-embed-v1")

        _, kwargs = mock_embed.call_args
        assert kwargs.get("model") == "models/custom-embed-v1"

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_passes_query_as_content(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_query

        mock_embed.return_value = make_embed_result()
        embed_query("what is fastapi?")

        _, kwargs = mock_embed.call_args
        assert kwargs.get("content") == "what is fastapi?"

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_embedding_values_match_mock(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_query

        fixed = [0.5, 0.6, 0.7]
        mock_embed.return_value = {"embedding": fixed}
        result = embed_query("query")

        np.testing.assert_array_almost_equal(result[0], fixed)

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_called_exactly_once(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_query

        mock_embed.return_value = make_embed_result()
        embed_query("only one call expected")

        mock_embed.assert_called_once()

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_api_error_raises_runtime_error(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_query

        mock_embed.side_effect = Exception("rate limit hit")

        with pytest.raises(RuntimeError) as exc_info:
            embed_query("query")

        assert "Error generating query embedding" in str(exc_info.value)
        assert "rate limit hit" in str(exc_info.value)

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_api_error_wraps_original_message(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_query

        mock_embed.side_effect = TimeoutError("connection timed out")

        with pytest.raises(RuntimeError) as exc_info:
            embed_query("query")

        assert "connection timed out" in str(exc_info.value)

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_result_is_2d_not_1d(self, mock_embed):
        """Ensures reshape(1, -1) produces a 2D array — compatible with FAISS."""
        from ai_chat.app.utils.embeddings import embed_query

        mock_embed.return_value = make_embed_result(dim=768)
        result = embed_query("query")

        assert result.ndim == 2


# ─────────────────────────────────────────────
# embed_texts vs embed_query — task_type contrast
# ─────────────────────────────────────────────

class TestTaskTypeContrast:

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_embed_texts_uses_document_not_query_task(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_texts

        mock_embed.return_value = make_embed_result()
        embed_texts(["doc"])

        _, kwargs = mock_embed.call_args
        assert kwargs["task_type"] != "retrieval_query"
        assert kwargs["task_type"] == "retrieval_document"

    @patch("ai_chat.app.utils.embeddings.genai.embed_content")
    def test_embed_query_uses_query_not_document_task(self, mock_embed):
        from ai_chat.app.utils.embeddings import embed_query

        mock_embed.return_value = make_embed_result()
        embed_query("q")

        _, kwargs = mock_embed.call_args
        assert kwargs["task_type"] != "retrieval_document"
        assert kwargs["task_type"] == "retrieval_query"