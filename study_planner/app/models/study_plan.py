from app.db.base import Base  # Use base.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime

class StudyPlan(Base):
    __tablename__ = "study_plans"
    __table_args__ = {"schema": "stud_hub_schema"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("stud_hub_schema.users.user_id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)  # text in DB
    course_count = Column(Integer, nullable=False, default=0)
    duration = Column(Integer, nullable=False, default=0)
    is_predefined = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default="now()", nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default="now()", onupdate=datetime.utcnow, nullable=False)

    # Relationships
    study_items = relationship("StudyItem", back_populates="study_plan")
