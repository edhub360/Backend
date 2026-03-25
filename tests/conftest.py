import pytest
import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock

# --- Add all service roots to PYTHONPATH ---
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "login"))
sys.path.insert(0, os.path.join(ROOT, "ai_chat"))
sys.path.insert(0, os.path.join(ROOT, "quiz"))
sys.path.insert(0, os.path.join(ROOT, "flashcard"))

# Set fake env vars BEFORE any module imports that read os.environ
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "fake-secret-key-for-testing")
os.environ.setdefault("GOOGLE_CLIENT_ID", "fake-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "fake-google-client-secret")
os.environ.setdefault("JWT_SECRET_KEY", "fake-jwt-secret-for-testing")

# Mock login app.config
_mock_cfg = MagicMock()
_mock_cfg.settings.jwt_secret_key = "fake-jwt-secret-for-testing"
_mock_cfg.settings.jwt_algorithm = "HS256"
_mock_cfg.settings.access_token_expire_minutes = 15
sys.modules["app"] = MagicMock()
sys.modules["app.config"] = _mock_cfg
sys.modules["app.utils"] = MagicMock(
    generate_secure_token=MagicMock(return_value="fake-token"),
    hash_token=MagicMock(return_value="fake-hash"),
)

# Fix bare 'from models import' in flashcard/main.py
import flashcard.models as _fc_models
sys.modules.setdefault("models", _fc_models)

# Fix bare 'from database import' in quiz/main.py and flashcard/main.py
import quiz.database as _qz_db
sys.modules.setdefault("database", _qz_db)


# --- Event loop ---
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# --- In-memory test database ---
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    from quiz.models import Base as QuizBase
    from login.app.models import Base as LoginBase
    async with engine.begin() as conn:
        await conn.run_sync(QuizBase.metadata.create_all)
        await conn.run_sync(LoginBase.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(QuizBase.metadata.drop_all)
        await conn.run_sync(LoginBase.metadata.drop_all)
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
        "jwt_secret_key": "test-secret-key-do-not-use-in-production-abc123",
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
