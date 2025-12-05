import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import event
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(
    DATABASE_URL, 
    future=True, 
    echo=False,
    pool_size=5,                    # Reduce pool size
    max_overflow=10,               # Allow some overflow
    pool_pre_ping=True,            # Validate connections before use
    pool_timeout=30,               # Connection timeout from pool
    pool_recycle=1800              # Recycle connections every 30 minutes
)

# Set search_path for all connections
@event.listens_for(engine.sync_engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("SET search_path TO stud_hub_schema, public")
    cursor.execute("SHOW search_path")
    current = cursor.fetchone()
    print("DB search_path:", current[0])
    cursor.close()

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Dependency
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
