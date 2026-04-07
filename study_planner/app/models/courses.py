# app/models/courses.py
from sqlalchemy import Column, String, Integer, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from study_planner.app.db.base import Base
from uuid import uuid4


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = {"schema": "stud_hub_schema"}

    course_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    course_title = Column(Text, nullable=False, default="")
    course_desc = Column(Text, nullable=True, default="")
    course_duration = Column(Integer, nullable=True)
    course_complexity = Column(Text, nullable=True, default="")
    course_owner = Column(Text, nullable=True, default="")
    course_url = Column(Text, nullable=True, default="")
    course_redirect_url = Column(Text, nullable=True, default="")
    course_image_url = Column(Text, nullable=True, default="")
    course_credit = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    course_code = Column(String(50), nullable=True, default="")
    course_category = Column(Text, nullable=True, default="")

    def __init__(self, **kwargs):
        kwargs.setdefault("course_id", uuid4())
        super().__init__(**kwargs)