import uuid
from sqlalchemy import Column, Integer, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from app.db import Base


class Course(Base):
    """
    Mirror of courses-service Course model.
    This service only inserts/upserts — never alters the schema.
    """
    __tablename__ = "courses"
    __table_args__ = {"schema": "stud_hub_schema"}

    course_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False
    )
    course_title = Column(Text, nullable=False)
    course_desc = Column(Text, nullable=True)
    course_duration = Column(Integer, nullable=True)
    course_complexity = Column(Text, nullable=True)
    course_owner = Column(Text, nullable=True)
    course_url = Column(Text, nullable=True)
    course_redirect_url = Column(Text, nullable=True)
    course_image_url = Column(Text, nullable=True)
    course_credit = Column(Integer, nullable=True)
    created_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now()  # DB sets this automatically on insert
    )