# app/schemas/course.py (UPDATED)
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class CourseBase(BaseModel):
    course_title: str
    course_code: Optional[str] = ""
    course_category: Optional[str] = ""
    course_duration: Optional[int]
    course_credit: Optional[int]

class CourseRead(CourseBase):
    course_id: UUID
    course_desc: Optional[str] = ""
    course_complexity: Optional[str] = ""
    course_owner: Optional[str] = ""
    course_url: Optional[str] = ""
    course_redirect_url: Optional[str] = ""
    course_image_url: Optional[str] = ""
    created_at: Optional[datetime] = None  # Import datetime if needed

    class Config:
        from_attributes = True  # ORM mode
