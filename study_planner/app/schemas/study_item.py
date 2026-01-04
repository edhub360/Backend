from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from .study_plan import StudyPlanRead  # Nested optional

class StudyItemBase(BaseModel):
    course_code: str
    title: str
    status: str = "planned"
    position_index: int = 0
    term_name: str = "Unknown"
    course_category: str = "Uncategorized"
    study_plan_id: Optional[UUID] = None
    course_id: Optional[UUID] = None

class StudyItemCreate(StudyItemBase):
    pass

class StudyItemRead(StudyItemBase):
    item_id: UUID
    user_id: UUID
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    study_plan: Optional[StudyPlanRead] = None

    class Config:
        from_attributes = True
