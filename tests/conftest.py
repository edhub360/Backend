import pytest
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    """Create test database engine with in-memory SQLite"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    
    # Import and create tables
    from quiz.models import Base as QuizBase
    from login.app.models import Base as LoginBase
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(QuizBase.metadata.create_all)
        await conn.run_sync(LoginBase.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(QuizBase.metadata.drop_all)
        await conn.run_sync(LoginBase.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create test database session"""
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
    """Mock application settings"""
    return {
        "jwt_secret_key": "test-secret-key-do-not-use-in-production",
        "jwt_algorithm": "HS256",
        "access_token_expire_minutes": 15,
        "google_client_id": "test-google-client-id",
    }


@pytest.fixture
def mock_google_verify(monkeypatch):
    """Mock Google token verification"""
    async def mock_verify(*args, **kwargs):
        return {
            "google_id": "123456789",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/pic.jpg"
        }
    
    monkeypatch.setattr(
        "login.app.auth.verify_google_token",
        mock_verify
    )


# --- Sample data fixtures ---
@pytest.fixture
def sample_user_data():
    """Sample user creation data"""
    return {
        "email": "test@example.com",
        "name": "Test User",
        "language": "en",
        "subscription_tier": "free",
    }


@pytest.fixture
def sample_quiz_data():
    """Sample quiz creation data"""
    return {
        "title": "Python Basics Quiz",
        "description": "Test your Python knowledge",
        "subject_tag": "Python",
        "difficulty_level": "beginner",
        "estimated_time": 30,
    }


@pytest.fixture
def sample_question_data():
    """Sample question creation data"""
    return {
        "question_text": "What is Python?",
        "correct_answer": "A programming language",
        "incorrect_answers": [
            "A snake species",
            "A type of coffee",
            "A brand of shoes"
        ],
        "explanation": "Python is a high-level programming language.",
        "difficulty": "beginner",
        "subject_tag": "Python",
    }

# Additional pytest configurations can be added here.
