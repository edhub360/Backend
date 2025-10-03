import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import urllib.parse

Base = declarative_base()

# --- Environment variables ---
DB_USER = os.getenv("DB_USER", "postgres")
DB_NAME = os.getenv("DB_NAME", "StudHub")
DB_PASS = os.getenv("DB_PASS", "Edhub@360")
DB_PASS = urllib.parse.quote_plus(DB_PASS)
#DB_PASS = os.getenv("DB_PASS")  # From Secret Manager
CLOUD_SQL_CONNECTION_NAME = os.getenv("CLOUD_SQL_CONNECTION_NAME")
USE_CLOUD_SQL_SOCKET = os.getenv("USE_CLOUD_SQL_SOCKET", "true").lower() == "true"

# --- DATABASE URL ---
if USE_CLOUD_SQL_SOCKET and CLOUD_SQL_CONNECTION_NAME:
    # Cloud Run / GCP: use Unix socket
    DATABASE_URL = (
        f"postgresql+asyncpg://{DB_USER}:{DB_PASS}"
        f"@/{DB_NAME}?host=/cloudsql/{CLOUD_SQL_CONNECTION_NAME}"
    )
else:
    # fallback (local dev or proxy)
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- SQLAlchemy async engine ---
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# --- Dependency ---
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
