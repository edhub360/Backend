from app.db.base import Base
from sqlalchemy.orm import relationship
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Integer, String
)
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from uuid import uuid4


class Term(Base):
    __tablename__ = "terms"
    __table_args__ = {"schema": "stud_hub_schema"}  # <-- add this

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    position_index = Column(Integer, nullable=False, default=0)
    is_archived = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    study_items = relationship(
        "StudyItem",
        back_populates="term",
        cascade="all, delete-orphan",
        order_by="StudyItem.position_index",
    )
