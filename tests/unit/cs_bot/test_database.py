"""tests/unit/cs_bot/test_database.py — init_vector_store and get_vector_store"""
import pytest
from unittest.mock import patch, MagicMock


class TestInitVectorStore:

    def _mock_settings(self):
        s = MagicMock()
        s.EMBEDDING_MODEL   = "models/gemini-embedding-001"
        s.GEMINI_API_KEY    = "fake-key"
        s.VECTOR_COLLECTION = "website_docs"
        s.PGVECTOR_URL      = "postgresql+psycopg_async://localhost/db"
        return s

    def test_sets_global_vector_store(self):
        mock_vs = MagicMock()
        with patch("app.core.database.GoogleGenerativeAIEmbeddings"),              patch("app.core.database.PGVector", return_value=mock_vs),              patch("app.core.database.settings", self._mock_settings()):
            import cs_bot.app.core.database as db_mod
            db_mod.vector_store = None
            db_mod.init_vector_store()
            assert db_mod.vector_store is mock_vs

    def test_sets_global_embeddings(self):
        mock_embed = MagicMock()
        with patch("cs_bot.app.core.database.GoogleGenerativeAIEmbeddings", return_value=mock_embed),              patch("cs_bot.app.core.database.PGVector"),              patch("cs_bot.app.core.database.settings", self._mock_settings()):
            import cs_bot.app.core.database as db_mod
            db_mod.embeddings = None
            db_mod.init_vector_store()
            assert db_mod.embeddings is mock_embed

    def test_embedding_uses_semantic_similarity_task(self):
        with patch("cs_bot.app.core.database.GoogleGenerativeAIEmbeddings") as mock_embed_cls,              patch("cs_bot.app.core.database.PGVector"),              patch("cs_bot.app.core.database.settings", self._mock_settings()):
            import cs_bot.app.core.database as db_mod
            db_mod.init_vector_store()
            kwargs = mock_embed_cls.call_args[1]
            assert kwargs["task_type"] == "semantic_similarity"

    def test_pgvector_async_mode_enabled(self):
        with patch("cs_bot.app.core.database.GoogleGenerativeAIEmbeddings"),              patch("cs_bot.app.core.database.PGVector") as mock_pg_cls,              patch("cs_bot.app.core.database.settings", self._mock_settings()):
            import cs_bot.app.core.database as db_mod
            db_mod.init_vector_store()
            kwargs = mock_pg_cls.call_args[1]
            assert kwargs["async_mode"] is True

    def test_pgvector_jsonb_enabled(self):
        with patch("cs_bot.app.core.database.GoogleGenerativeAIEmbeddings"),              patch("cs_bot.app.core.database.PGVector") as mock_pg_cls,              patch("cs_bot.app.core.database.settings", self._mock_settings()):
            import cs_bot.app.core.database as db_mod
            db_mod.init_vector_store()
            kwargs = mock_pg_cls.call_args[1]
            assert kwargs["use_jsonb"] is True

    def test_pgvector_does_not_pre_delete_collection(self):
        with patch("cs_bot.app.core.database.GoogleGenerativeAIEmbeddings"),              patch("cs_bot.app.core.database.PGVector") as mock_pg_cls,              patch("cs_bot.app.core.database.settings", self._mock_settings()):
            import cs_bot.app.core.database as db_mod
            db_mod.init_vector_store()
            kwargs = mock_pg_cls.call_args[1]
            assert kwargs["pre_delete_collection"] is False


class TestGetVectorStore:

    def test_returns_initialized_store(self):
        mock_vs = MagicMock()
        import cs_bot.app.core.database as db_mod
        db_mod.vector_store = mock_vs
        assert db_mod.get_vector_store() is mock_vs

    def test_returns_none_before_init(self):
        import cs_bot.app.core.database as db_mod
        db_mod.vector_store = None
        assert db_mod.get_vector_store() is None
