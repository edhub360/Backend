from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime


class CoursePreview(BaseModel):
    course_id: UUID
    course_title: str
    course_desc: Optional[str]          # ✅ was short_description
    course_duration: Optional[int]
    course_complexity: Optional[str]
    course_image_url: Optional[str]
    course_redirect_url: Optional[str]
    course_credit: Optional[int]

    class Config:
        from_attributes = True          # Pydantic v2 ORM mode


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
    created_at: datetime               # use datetime not str

    class Config:
        from_attributes = True


class PaginatedCourses(BaseModel):
    total: int
    page: int
    limit: int
    items: list[CoursePreview]         # no Column declarations