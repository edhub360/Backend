"""tests/unit/cs_bot/conftest.py"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

# Must be set BEFORE any app module is imported
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["DATABASE_URL"]   = "postgresql+asyncpg://user:pass@localhost/testdb"
os.environ["REDIS_URL"]      = "redis://localhost:6379"
os.environ["ADMIN_KEY"]      = "test-admin-secret"

# Pre-register sub-modules so patch("cs_bot.app.X.Y.symbol") resolves correctly.
# Python only adds a sub-module to sys.modules after it has been imported at least
# once; without this, patch() raises AttributeError: module has no attribute X.
import cs_bot.app.core.database              # noqa: E402
import cs_bot.app.core.redis                 # noqa: E402
import cs_bot.app.services.ingestion_service # noqa: E402
import cs_bot.app.services.session_service   # noqa: E402


@pytest.fixture
def mock_redis():
    r        = AsyncMock()
    r.get    = AsyncMock(return_value=None)
    r.setex  = AsyncMock()
    r.delete = AsyncMock()
    r.aclose = AsyncMock()
    return r


@pytest.fixture
def mock_vector_store():
    vs                = MagicMock()
    vs.as_retriever   = MagicMock(return_value=AsyncMock())
    vs.aadd_documents = AsyncMock(return_value=None)
    return vs