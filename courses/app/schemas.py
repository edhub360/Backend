from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

class CoursePreview(BaseModel):
    course_id: UUID
    course_title: str
    short_description: Optional[str]
    course_duration: Optional[int]
    course_complexity: Optional[str]
    course_image_url: Optional[str]
    course_redirect_url: Optional[str]
    course_credit: Optional[int]

class CourseDetail(BaseModel):
    course_id: UUID
    course_title: str
    course_desc: Optional[str]
    course_duration: Optional[int]
    course_complexity: Optional[str]
    course_owner: Optional[str]
    course_url: Optional[str]
    course_redirect_url: Optional[str]
    course_image_url: Optional[str]
    course_credit: Optional[int]
    created_at: str # ISO format

class PaginatedCourses(BaseModel):
    total: int
    page: int
    limit: int
    items: list[CoursePreview]
