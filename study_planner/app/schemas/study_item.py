from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.study_item import STUDY_STATUS_ENUM
from app.schemas.requirement_category import RequirementCategoryRead

class StudyItemBase(BaseModel):
    # Keep existing ID fields for backward compat
    term_id: Optional[UUID] = None
    requirement_category_id: Optional[UUID] = None
    # NEW name fields for denormalization
    term_name: Optional[str] = None
    requirement_category_name: Optional[str] = None
    course_code: str = Field(..., max_length=64)
    title: str = Field(..., max_length=255)
    units: int = Field(..., gt=0)
    status: str = Field(default="planned", pattern="^(planned|locked|completed|in_progress)$")
    position_index: int = 0
    notes: Optional[str] = None

class StudyItemCreate(StudyItemBase):
    """Accepts EITHER IDs OR names - zero frontend changes needed"""
    pass

class StudyItemUpdate(StudyItemBase):
    """All fields optional for PATCH"""
    term_id: Optional[UUID] = None
    requirement_category_id: Optional[UUID] = None
    term_name: Optional[str] = None
    requirement_category_name: Optional[str] = None
    course_code: Optional[str] = Field(None, max_length=64)
    title: Optional[str] = Field(None, max_length=255)
    units: Optional[int] = Field(None, gt=0)
    status: Optional[str] = Field(None, pattern="^(planned|locked|completed|in_progress)$")
    position_index: Optional[int] = None
    notes: Optional[str] = None

class StudyItemRead(BaseModel):
    id: UUID
    user_id: UUID
    # BACKWARD COMPAT + NEW FIELDS
    term_id: Optional[UUID] = None
    term_name: str  # NEW - "Fall 2025" ✅
    requirement_category_id: Optional[UUID] = None
    requirement_category_name: str  # NEW - "Core CS" ✅
    course_code: str
    title: str
    units: int
    status: str
    position_index: int
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
