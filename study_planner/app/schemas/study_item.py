from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.study_item import STUDY_STATUS_ENUM
from app.schemas.requirement_category import RequirementCategoryRead


class StudyItemBase(BaseModel):
    term_id: UUID
    requirement_category_id: Optional[UUID] = None
    course_code: str = Field(..., max_length=64)
    title: str = Field(..., max_length=255)
    units: int = Field(..., gt=0)
    status: str = Field(default="planned", pattern="^(planned|locked|completed|in_progress)$")
    position_index: int = 0
    notes: Optional[str] = None


class StudyItemCreate(StudyItemBase):
    pass


class StudyItemUpdate(BaseModel):
    term_id: Optional[UUID] = None
    requirement_category_id: Optional[UUID] = None
    course_code: Optional[str] = Field(None, max_length=64)
    title: Optional[str] = Field(None, max_length=255)
    units: Optional[int] = Field(None, gt=0)
    status: Optional[str] = Field(
        None, pattern="^(planned|locked|completed|in_progress)$"
    )
    position_index: Optional[int] = None
    notes: Optional[str] = None


class StudyItemRead(BaseModel):
    id: UUID
    term_id: UUID
    requirement_category_id: Optional[UUID]   # <- use ID, not relationship
    course_code: str
    title: str
    units: int
    status: str
    position_index: int
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
 
