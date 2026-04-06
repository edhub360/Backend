import pytest
import asyncio
import sys
import types
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import String, JSON, DateTime
import quiz.models as _qz_models
import flashcard.models as _fc_models
import quiz.schemas as _qz_schemas
import flashcard.schemas as _fc_schemas
import quiz.database as _qz_db

def _merge(name, *sources):
    mod = types.ModuleType(name)
    for src in sources:
        for attr in dir(src):
            if not attr.startswith("__"):
                setattr(mod, attr, getattr(src, attr))
    sys.modules[name] = mod

_merge("models", _qz_models, _fc_models)
_merge("schemas", _qz_schemas, _fc_schemas)
sys.modules.setdefault("database", _qz_db)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_engine():
    from quiz.models import Base as QuizBase
    from flashcard.models import Base as FlashcardBase

    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    from sqlalchemy import event
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    for metadata in [QuizBase.metadata, FlashcardBase.metadata]:
        for table in metadata.tables.values():
            table.schema = None
            for col in table.columns:
                type_name = col.type.__class__.__name__
                if type_name == "UUID":
                    col.type = String(36)
                    col.server_default = None
                elif type_name == "JSONB":
                    col.type = JSON()
                elif type_name in ("TIMESTAMP", "DateTime", "DATETIME"):
                    col.type = DateTime()
                    col.server_default = None
                elif type_name == "ARRAY":
                    col.type = JSON()
                    col.server_default = None

    async with engine.begin() as conn:
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