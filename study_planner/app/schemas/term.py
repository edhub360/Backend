from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.study_item import StudyItemRead


class TermBase(BaseModel):
    name: str = Field(..., max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    position_index: int = 0
    is_archived: bool = False


class TermCreate(TermBase):
    pass


class TermUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    position_index: Optional[int] = None
    is_archived: Optional[bool] = None


class TermRead(BaseModel):
    id: UUID
    name: str
    start_date: Optional[date]
    end_date: Optional[date]
    position_index: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    study_items: list[StudyItemRead] = []

    class Config:
        from_attributes = True
