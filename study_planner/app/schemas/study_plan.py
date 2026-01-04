from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class StudyPlanBase(BaseModel):
    name: str
    description: Optional[str] = None
    course_count: int = 0
    duration: int = 0

class StudyPlanCreate(StudyPlanBase):
    pass

class StudyPlanUpdate(StudyPlanBase):
    name: Optional[str] = None
    description: Optional[str] = None

class StudyPlanRead(StudyPlanBase):
    id: UUID
    user_id: UUID
    is_predefined: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
