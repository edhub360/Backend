from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase   # use this instead of declarative_base()
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,          # set True only in dev, not prod
    pool_pre_ping=True,  # auto-reconnect if DB connection drops (Cloud SQL)
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,     # prevent accidental implicit flushes
)

class Base(DeclarativeBase):   # modern SQLAlchemy 2.0 style
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()   # rollback on error
            raise
        finally:
            await session.close()