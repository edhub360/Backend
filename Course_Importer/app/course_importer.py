import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from app.models import Course
from datetime import datetime, timezone

async def upsert_courses(db: AsyncSession, rows: list[dict]) -> dict:
    inserted = 0
    skipped = 0

    for row in rows:
        if not row:
            skipped += 1
            continue

        stmt = insert(Course).values(
            course_id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
            **row
        ).on_conflict_do_nothing(
            index_elements=["course_title"]  # treat title as unique key
        )

        result = await db.execute(stmt)
        if result.rowcount > 0:
            inserted += 1
        else:
            skipped += 1

    await db.commit()
    return {"inserted": inserted, "skipped": skipped}