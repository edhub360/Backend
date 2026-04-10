"""tests/unit/cs_bot/conftest.py"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

# Set env before app imports
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/testdb"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["ADMIN_KEY"] = "test-admin-secret"

# IMPORTANT:
# Do not import cs_bot app modules here.
# pytest imports conftest before test collection, so any heavy import here can
# crash the whole test run. Keep conftest limited to pure fixtures/env only.

@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.setex = AsyncMock()
    r.delete = AsyncMock()
    r.aclose = AsyncMock()
    return r


@pytest.fixture
def mock_vector_store():
    vs = MagicMock()
    vs.as_retriever = MagicMock(return_value=AsyncMock())
    vs.aadd_documents = AsyncMock(return_value=None)
    return vs