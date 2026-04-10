"""
tests/unit/cs_bot/conftest.py
Shared fixtures and env setup for all cs_bot unit tests.
No real DB, Redis, or Gemini connections.
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/testdb"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["ADMIN_KEY"] = "test-admin-secret"


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