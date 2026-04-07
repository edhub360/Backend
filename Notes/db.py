import os
import importlib
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import event
from dotenv import load_dotenv


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")


# DeclarativeBase is used (not the legacy declarative_base()) so that
# issubclass(Model, sqlalchemy.orm.decl_api.Base) resolves to True in tests.
class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    DATABASE_URL,
    future=True,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_timeout=30,
    pool_recycle=1800,
)


# Set search_path for all connections.
# NOTE: This event listener is intentionally NOT guarded by a dialect check.
# Tests that need to avoid this behaviour supply a mock engine (via
# importlib.reload + patch) so the listener is never registered on the
# SQLite engine used in unit tests.
@event.listens_for(engine.sync_engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("SET search_path TO stud_hub_schema, public")
    cursor.execute("SHOW search_path")
    current = cursor.fetchone()
    print("DB search_path:", current[0])
    cursor.close()


AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Dependency
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session