"""tests/unit/cs_bot/test_config.py — Settings and PGVECTOR_URL property"""
import pytest
from unittest.mock import patch


class TestSettings:

    def test_pgvector_url_replaces_asyncpg_with_psycopg(self):
        with patch.dict("os.environ", {
            "GEMINI_API_KEY": "key",
            "DATABASE_URL":   "postgresql+asyncpg://user:pass@localhost/db",
            "REDIS_URL":      "redis://localhost:6379",
        }):
            from cs_bot.app.core.config import Settings
            s = Settings()
            assert s.PGVECTOR_URL == "postgresql+psycopg_async://user:pass@localhost/db"

    def test_pgvector_url_unchanged_when_no_asyncpg(self):
        with patch.dict("os.environ", {
            "GEMINI_API_KEY": "key",
            "DATABASE_URL":   "postgresql+psycopg_async://user:pass@localhost/db",
            "REDIS_URL":      "redis://localhost:6379",
        }):
            from cs_bot.app.core.config import Settings
            s = Settings()
            assert "asyncpg" not in s.PGVECTOR_URL

    def test_default_values(self):
        from cs_bot.app.core.config import settings
        assert settings.APP_NAME             == "Chatbot Service"
        assert settings.RETRIEVER_TOP_K      == 4
        assert settings.SESSION_TTL_SECONDS  == 3600
        assert settings.CHAT_MODEL           == "gemini-2.5-flash"

    def test_admin_key_default(self):
        from cs_bot.app.core.config import settings
        assert settings.ADMIN_KEY == "edhub360-admin-secret"

    def test_embedding_model_default(self):
        from cs_bot.app.core.config import settings
        assert settings.EMBEDDING_MODEL == "models/gemini-embedding-001"

    def test_vector_collection_default(self):
        from cs_bot.app.core.config import settings
        assert settings.VECTOR_COLLECTION == "website_docs"

    def test_collection_table_default(self):
        from cs_bot.app.core.config import settings
        assert settings.COLLECTION_TABLE == "csbot_collection"

    def test_embedding_table_default(self):
        from cs_bot.app.core.config import settings
        assert settings.EMBEDDING_TABLE == "csbot_embedding"
