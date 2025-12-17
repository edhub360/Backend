from app.db.base import Base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4


class RequirementCategory(Base):
    __tablename__ = "requirement_categories"
    __table_args__ = {"schema": "stud_hub_schema"}  

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    short_code = Column(String(64), nullable=True)
    color = Column(String(32), nullable=True)

    study_items = relationship("StudyItem", back_populates="requirement_category")
