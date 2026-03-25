import pytest
import asyncio
import os
import sys
import types
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock

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

# Add this block near the top of conftest.py, with the other sys.modules mocks
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

# --- Build a combined 'models' proxy from both quiz.models and flashcard.models ---
# Both services use bare `from models import ...` — we merge both into one proxy module
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

# Fix bare 'from schemas import' — merge quiz.schemas and flashcard.schemas into proxy
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
    from sqlalchemy import String, JSON
    from sqlalchemy.dialects.postgresql import JSONB

    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    from quiz.models import Base as QuizBase
    from flashcard.models import Base as FlashcardBase

    # Remap Postgres-only types → SQLite-compatible equivalents
    for metadata in [QuizBase.metadata, FlashcardBase.metadata]:
        for table in metadata.tables.values():
            table.schema = None  # ← strip 'stud_hub_schema' — SQLite has no schemas
            for col in table.columns:
                type_name = col.type.__class__.__name__
                if type_name == "UUID":
                    col.type = String(36)
                elif type_name == "JSONB":
                    col.type = JSON()

    async with engine.begin() as conn:
        await conn.run_sync(QuizBase.metadata.create_all)
        await conn.run_sync(FlashcardBase.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(QuizBase.metadata.drop_all)
        await conn.run_sync(FlashcardBase.metadata.drop_all)
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
