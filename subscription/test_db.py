# test_db.py
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
DATABASE_URL = "postgresql+asyncpg://postgres:Edhub%40360@localhost:5432/StudHub"
engine = create_async_engine(DATABASE_URL)

async def test():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        print("✅ DB connected!")
        print(result.scalar())  # Should print 1

asyncio.run(test())
