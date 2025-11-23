import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import urllib.parse
#from dotenv import load_dotenv

# Load environment variables from .env file (only in local development)
#load_dotenv()

Base = declarative_base()

# Get DATABASE_URL from environment
#DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_URL = os.environ["DATABASE_URL"]

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
