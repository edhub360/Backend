"""tests/unit/cs_bot/test_database.py"""
# conftest.py has already stubbed all langchain packages permanently.
# No local sys.modules patching needed here — just import directly.
from unittest.mock import MagicMock, patch
import cs_bot.app.core.database as db_mod


def _reset():
    db_mod.vector_store = None
    db_mod.embeddings   = None


class TestInitVectorStore:

    def test_sets_global_vector_store(self):
        mock_vs = MagicMock()
        _reset()
        with patch.multiple(
            "cs_bot.app.core.database",
            GoogleGenerativeAIEmbeddings=MagicMock(return_value=MagicMock()),
            PGVector=MagicMock(return_value=mock_vs),
        ):
            db_mod.init_vector_store()
        assert db_mod.vector_store is mock_vs

    def test_sets_global_embeddings(self):
        mock_emb = MagicMock()
        _reset()
        with patch.multiple(
            "cs_bot.app.core.database",
            GoogleGenerativeAIEmbeddings=MagicMock(return_value=mock_emb),
            PGVector=MagicMock(),
        ):
            db_mod.init_vector_store()
        assert db_mod.embeddings is mock_emb

    def test_embedding_uses_semantic_similarity_task(self):
        mock_emb_cls = MagicMock()
        _reset()
        with patch.multiple(
            "cs_bot.app.core.database",
            GoogleGenerativeAIEmbeddings=mock_emb_cls,
            PGVector=MagicMock(),
        ):
            db_mod.init_vector_store()
        _, kwargs = mock_emb_cls.call_args
        assert kwargs.get("task_type") == "semantic_similarity"

    def test_pgvector_async_mode_enabled(self):
        mock_pg_cls = MagicMock()
        _reset()
        with patch.multiple(
            "cs_bot.app.core.database",
            GoogleGenerativeAIEmbeddings=MagicMock(),
            PGVector=mock_pg_cls,
        ):
            db_mod.init_vector_store()
        _, kwargs = mock_pg_cls.call_args
        assert kwargs.get("async_mode") is True

    def test_pgvector_use_jsonb_enabled(self):
        mock_pg_cls = MagicMock()
        _reset()
        with patch.multiple(
            "cs_bot.app.core.database",
            GoogleGenerativeAIEmbeddings=MagicMock(),
            PGVector=mock_pg_cls,
        ):
            db_mod.init_vector_store()
        _, kwargs = mock_pg_cls.call_args
        assert kwargs.get("use_jsonb") is True

    def test_pgvector_does_not_pre_delete_collection(self):
        mock_pg_cls = MagicMock()
        _reset()
        with patch.multiple(
            "cs_bot.app.core.database",
            GoogleGenerativeAIEmbeddings=MagicMock(),
            PGVector=mock_pg_cls,
        ):
            db_mod.init_vector_store()
        _, kwargs = mock_pg_cls.call_args
        assert kwargs.get("pre_delete_collection") is False


class TestGetVectorStore:

    def test_returns_initialized_store(self):
        mock_vs = MagicMock()
        db_mod.vector_store = mock_vs
        assert db_mod.get_vector_store() is mock_vs

    def test_returns_none_before_init(self):
        db_mod.vector_store = None
        assert db_mod.get_vector_store() is None