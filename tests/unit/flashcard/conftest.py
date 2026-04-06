import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import String, JSON, DateTime, event

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_engine():
    from flashcard.models import Base as FlashcardBase

    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_pragma(dbapi_conn, _):
        dbapi_conn.cursor().execute("PRAGMA foreign_keys=OFF")

    for table in FlashcardBase.metadata.tables.values():
        table.schema = None
        for col in table.columns:
            t = col.type.__class__.__name__
            if t == "UUID":
                col.type = String(36); col.server_default = None
            elif t == "JSONB":
                col.type = JSON()
            elif t in ("TIMESTAMP", "DateTime", "DATETIME"):
                col.type = DateTime(); col.server_default = None
            elif t == "ARRAY":
                col.type = JSON(); col.server_default = None

    async with engine.begin() as conn:
        await conn.run_sync(FlashcardBase.metadata.create_all, checkfirst=True)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(FlashcardBase.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession,
        expire_on_commit=False, autoflush=False,
    )
    async with async_session() as session:
        yield session