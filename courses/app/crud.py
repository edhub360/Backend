from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.models import Course

async def get_course(session: AsyncSession, course_id: str):
    query = select(Course).where(Course.course_id == course_id)
    result = await session.execute(query)
    course = result.scalar_one_or_none()
    return course

async def list_courses(
    session: AsyncSession,
    q: Optional[str],
    page: int,
    limit: int,
    complexity: Optional[str],
    min_duration: Optional[int],
    max_duration: Optional[int]
):
    filters = []
    if q:
        stmt = or_(
            Course.course_title.ilike(f"%{q}%"),
            Course.course_desc.ilike(f"%{q}%")
        )
        filters.append(stmt)
    if complexity:
        filters.append(Course.course_complexity == complexity)
    if min_duration:
        filters.append(Course.course_duration >= min_duration)
    if max_duration:
        filters.append(Course.course_duration <= max_duration)
    
    base_query = select(Course).where(and_(*filters)) if filters else select(Course)

    # Count
    count_stmt = select(func.count()).select_from(Course).where(and_(*filters)) if filters else select(func.count()).select_from(Course)
    total = await session.scalar(count_stmt)

    # Pagination
    offset = (page - 1) * limit
    query = base_query.offset(offset).limit(limit)
    result = await session.execute(query)
    courses = result.scalars().all()

    return total, courses
