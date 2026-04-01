import pytest
import asyncio
import os
import sys
import types
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock
from sqlalchemy import String, JSON
from flashcard.models import Quiz, QuizQuestion, FlashcardAnalytics

# --- Add all service roots to PYTHONPATH ---
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "login"))
sys.path.insert(0, os.path.join(ROOT, "ai_chat"))
sys.path.insert(0, os.path.join(ROOT, "quiz"))
sys.path.insert(0, os.path.join(ROOT, "flashcard"))


# --- Set fake env vars BEFORE any module imports that read os.environ ---
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "fake-secret-key-for-testing")
os.environ.setdefault("GOOGLE_CLIENT_ID", "fake-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "fake-google-client-secret")
os.environ.setdefault("JWT_SECRET_KEY", "fake-jwt-secret-for-testing")
os.environ.setdefault("GEMINI_API_KEY", "fake-gemini-api-key")
os.environ.setdefault("STRIPE_SECRET_KEY", "fake-stripe-secret-key")


# --- Mock app.db with a real DeclarativeBase so login/app/models.py can import it ---
class _TestBase(DeclarativeBase):
    pass


_mock_db = MagicMock()
_mock_db.Base = _TestBase


# --- Mock app namespace BEFORE any login imports ---
_mock_cfg = MagicMock()
_mock_cfg.settings.jwt_secret_key = "fake-jwt-secret-for-testing"
_mock_cfg.settings.jwt_algorithm = "HS256"
_mock_cfg.settings.access_token_expire_minutes = 15


_mock_app_pkg = types.ModuleType("app")
sys.modules["app"] = _mock_app_pkg
sys.modules["app.config"] = _mock_cfg
sys.modules["app.db"] = _mock_db
sys.modules["app.utils"] = MagicMock(
    generate_secure_token=MagicMock(return_value="fake-token"),
    hash_token=MagicMock(return_value="fake-hash"),
)


# --- Mock google.cloud.storage ---
import types as _types

_mock_gcs = _types.ModuleType("google.cloud.storage")
_mock_gcs.Client = MagicMock()

_google_mod = sys.modules.get("google") or _types.ModuleType("google")
_google_cloud_mod = sys.modules.get("google.cloud") or _types.ModuleType("google.cloud")
_google_cloud_mod.storage = _mock_gcs

sys.modules["google"] = _google_mod
sys.modules["google.cloud"] = _google_cloud_mod
sys.modules["google.cloud.storage"] = _mock_gcs
sys.modules["pandas"] = MagicMock()


# --- Mock ai_chat external dependencies (langchain, gemini, etc.) ---
# These must be mocked BEFORE ai_chat modules are imported
_mock_langchain = MagicMock()
_mock_langchain_core = MagicMock()
_mock_langchain_google = MagicMock()

sys.modules.setdefault("langchain", _mock_langchain)
sys.modules.setdefault("langchain.chains", _mock_langchain)
sys.modules.setdefault("langchain.memory", _mock_langchain)
sys.modules.setdefault("langchain.prompts", _mock_langchain)
sys.modules.setdefault("langchain_core", _mock_langchain_core)
sys.modules.setdefault("langchain_core.messages", _mock_langchain_core)
sys.modules.setdefault("langchain_core.prompts", _mock_langchain_core)
sys.modules.setdefault("langchain_core.output_parsers", _mock_langchain_core)
sys.modules.setdefault("langchain_google_genai", _mock_langchain_google)
sys.modules.setdefault("google.generativeai", MagicMock())
sys.modules.setdefault("google.generativeai.types", MagicMock())


# --- Build a combined 'models' proxy from both quiz.models and flashcard.models ---
import quiz.models as _qz_models
import flashcard.models as _fc_models

_combined_models = types.ModuleType("models")

for _attr in dir(_qz_models):
    if not _attr.startswith("__"):
        setattr(_combined_models, _attr, getattr(_qz_models, _attr))

for _attr in dir(_fc_models):
    if not _attr.startswith("__"):
        setattr(_combined_models, _attr, getattr(_fc_models, _attr))

sys.modules["models"] = _combined_models


# --- Fix bare 'from schemas import' — merge quiz.schemas and flashcard.schemas ---
import quiz.schemas as _qz_schemas
import flashcard.schemas as _fc_schemas

_combined_schemas = types.ModuleType("schemas")

for _attr in dir(_qz_schemas):
    if not _attr.startswith("__"):
        setattr(_combined_schemas, _attr, getattr(_qz_schemas, _attr))

for _attr in dir(_fc_schemas):
    if not _attr.startswith("__"):
        setattr(_combined_schemas, _attr, getattr(_fc_schemas, _attr))

sys.modules["schemas"] = _combined_schemas


# --- Fix bare 'from database import' used inside quiz/main.py ---
import quiz.database as _qz_db
sys.modules.setdefault("database", _qz_db)



# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    from sqlalchemy import String, JSON, DateTime, event
    from sqlalchemy.ext.asyncio import AsyncConnection

    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Disable FK enforcement in SQLite so cross-schema FK strings don't crash
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    # In conftest.py, before create_all
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy import JSON
    from sqlalchemy.dialects import sqlite

    # Register JSONB → JSON for SQLite
    JSONB.__init__ = lambda self, *a, **kw: super(JSONB, self).__init__(*a, **kw)

    # Simpler: just switch to JSON in the model for non-PG dialects

    from quiz.models import Base as QuizBase
    from flashcard.models import Base as FlashcardBase

    # Remap Postgres-only column types → SQLite-compatible equivalents
    for metadata in [QuizBase.metadata, FlashcardBase.metadata]:
        for table in metadata.tables.values():
            table.schema = None
            for col in table.columns:
                type_name = col.type.__class__.__name__
                if type_name == "UUID":
                    col.type = String(36)
                    col.server_default = None       # strip gen_random_uuid()
                elif type_name == "JSONB":
                    col.type = JSON()
                elif type_name in ("TIMESTAMP", "DateTime", "DATETIME"):
                    col.type = DateTime()
                    col.server_default = None       # strip now()
                elif type_name == "ARRAY":
                    col.type = JSON()
                    col.server_default = None

    async with engine.begin() as conn:
        # create_all with checkfirst avoids duplicate table errors across tests
        await conn.run_sync(QuizBase.metadata.create_all, checkfirst=True)
        await conn.run_sync(FlashcardBase.metadata.create_all, checkfirst=True)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(FlashcardBase.metadata.drop_all)
        await conn.run_sync(QuizBase.metadata.drop_all)
    await engine.dispose()



@pytest.fixture
async def test_session(test_engine):
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with async_session() as session:
        yield session


@pytest.fixture
def mock_settings():
    return {
        "jwt_secret_key": "fake-jwt-secret-for-testing",
        "jwt_algorithm": "HS256",
        "access_token_expire_minutes": 15,
        "google_client_id": "fake-google-client-id",
    }


@pytest.fixture
def mock_google_verify(monkeypatch):
    async def mock_verify(*args, **kwargs):
        return {
            "google_id": "123456789",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/pic.jpg",
        }
    monkeypatch.setattr("login.app.auth.verify_google_token", mock_verify)


@pytest.fixture
def sample_user_data():
    return {
        "email": "test@example.com",
        "name": "Test User",
        "language": "en",
        "subscription_tier": "free",
    }


@pytest.fixture
def sample_quiz_data():
    return {
        "title": "Python Basics Quiz",
        "description": "Test your Python knowledge",
        "subject_tag": "Python",
        "difficulty_level": "beginner",
        "estimated_time": 30,
    }


@pytest.fixture
def sample_question_data():
    return {
        "question_text": "What is Python?",
        "correct_answer": "A programming language",
        "incorrect_answers": ["A snake species", "A type of coffee", "A brand of shoes"],
        "explanation": "Python is a high-level programming language.",
        "difficulty": "beginner",
        "subject_tag": "Python",
    }


# ─────────────────────────────────────────────
# AI Chat fixtures
# ─────────────────────────────────────────────

@pytest.fixture
async def client():
    """Async HTTP client for ai_chat FastAPI app (named 'client' to match test files)."""
    from httpx import AsyncClient, ASGITransport
    from ai_chat.app.main import app as ai_chat_app

    async with AsyncClient(
        transport=ASGITransport(app=ai_chat_app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def mock_ai_chat_service(monkeypatch):
    """Mock the AIChatService so tests never call real LLM."""
    mock_service = MagicMock()
    mock_service.get_response = MagicMock(return_value="Mocked AI response")
    mock_service.stream_response = MagicMock(return_value=iter(["Mocked", " stream"]))
    monkeypatch.setattr(
        "ai_chat.app.modules.ai_chat.router.AIChatService",
        MagicMock(return_value=mock_service)
    )
    return mock_service
 