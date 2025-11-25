from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import PaginatedCourses, CourseDetail, CoursePreview
from app.crud import get_course, list_courses
from app.db import get_db
from app.utils.pagination import validate_pagination
import os

router = APIRouter()

MAX_PAGE_LIMIT = int(os.getenv("MAX_PAGE_LIMIT", 100))
PAGE_DEFAULT_LIMIT = int(os.getenv("PAGE_DEFAULT_LIMIT", 10))

@router.get("/", response_model=PaginatedCourses)
async def list_courses_endpoint(
    q: Optional[str] = Query(None, description="Keyword search"),
    page: int = Query(1, ge=1),
    limit: int = Query(PAGE_DEFAULT_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    complexity: Optional[str] = Query(None, description="Course complexity"),
    min_duration: Optional[int] = Query(None, ge=0),
    max_duration: Optional[int] = Query(None, ge=0),
    db: AsyncSession = Depends(get_db)
):
    try:
        validate_pagination(page, limit, MAX_PAGE_LIMIT)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    total, courses = await list_courses(db, q, page, limit, complexity, min_duration, max_duration)
    items = [
        CoursePreview(
            course_id=x.course_id,
            course_title=x.course_title,
            short_description=(x.course_desc[:200] if x.course_desc else ""),
            course_duration=x.course_duration,
            course_complexity=x.course_complexity,
            course_image_url=x.course_image_url,
            course_redirect_url=x.course_redirect_url,
            course_credit=x.course_credit
        )
        for x in courses
    ]
    # Move last item to first, rest shifted down
    if items:
        items = [items[-1]] + items[:-1]
    return PaginatedCourses(total=total, page=page, limit=limit, items=items)

@router.get("/{course_id}", response_model=CourseDetail)
async def get_course_endpoint(
    course_id: str,
    db: AsyncSession = Depends(get_db)
):
    course = await get_course(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseDetail(
        course_id=course.course_id,
        course_title=course.course_title,
        course_desc=course.course_desc,
        course_duration=course.course_duration,
        course_complexity=course.course_complexity,
        course_owner=course.course_owner,
        course_url=course.course_url,
        course_redirect_url=course.course_redirect_url,
        course_image_url=course.course_image_url,
        course_credit=course.course_credit,
        created_at=course.created_at.isoformat()
    )

@router.get("/featured", response_model=PaginatedCourses)
async def featured_courses_endpoint(
    limit: int = Query(PAGE_DEFAULT_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: AsyncSession = Depends(get_db)
):
    # Return most recent courses as 'featured'
    total, courses = await list_courses(db, None, 1, limit, None, None, None)
    items = [
        CoursePreview(
            course_id=x.course_id,
            course_title=x.course_title,
            short_description=(x.course_desc[:200] if x.course_desc else ""),
            course_duration=x.course_duration,
            course_complexity=x.course_complexity,
            course_image_url=x.course_image_url,
            course_redirect_url=x.course_redirect_url,
            course_credit=x.course_credit
        )
        for x in courses
    ]
    return PaginatedCourses(total=total, page=1, limit=limit, items=items)
