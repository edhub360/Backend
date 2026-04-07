# app/schemas/courses.py
from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class CourseBase(BaseModel):
    course_title: str
    course_code: Optional[str] = ""
    course_category: Optional[str] = ""
    course_duration: Optional[int] = None  # ← was missing = None
    course_credit: Optional[int] = None    # ← was missing = None


class CourseRead(CourseBase):
    course_id: UUID
    course_desc: Optional[str] = ""
    course_complexity: Optional[str] = ""
    course_owner: Optional[str] = ""
    course_url: Optional[str] = ""
    course_redirect_url: Optional[str] = ""
    course_image_url: Optional[str] = ""
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)  # ← replaces class Config