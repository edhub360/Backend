from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RequirementCategoryBase(BaseModel):
    name: str = Field(..., max_length=255)
    short_code: Optional[str] = Field(None, max_length=64)
    color: Optional[str] = Field(None, max_length=32)


class RequirementCategoryCreate(RequirementCategoryBase):
    pass


class RequirementCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    short_code: Optional[str] = Field(None, max_length=64)
    color: Optional[str] = Field(None, max_length=32)


class RequirementCategoryRead(BaseModel):
    id: UUID
    name: str
    short_code: Optional[str]
    color: Optional[str]

    class Config:
        from_attributes = True
