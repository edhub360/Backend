from app.db.base import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ENUM
from uuid import uuid4
from sqlalchemy.orm import relationship
from datetime import datetime


class StudyItem(Base):
    __tablename__ = "study_items"
    __table_args__ = {"schema": "stud_hub_schema"}
    
    item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    course_code = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(
        ENUM('planned', 'locked', 'completed', 'in_progress',
             name='study_status_enum', schema='stud_hub_schema', create_type=False),
        nullable=False, default='planned'
    )
    position_index = Column(Integer, nullable=False, default=0)
    term_name = Column(String(100), nullable=False, default='Unknown')
    course_category = Column(String(100), nullable=False, default='Uncategorized')
    study_plan_id = Column(UUID(as_uuid=True), ForeignKey("stud_hub_schema.study_plans.id", ondelete="CASCADE"), nullable=True)
    course_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default="now()")
    updated_at = Column(DateTime(timezone=True), server_default="now()", onupdate=datetime.utcnow)


    study_plan = relationship("StudyPlan", back_populates="study_items")
