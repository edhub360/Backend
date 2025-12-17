from app.db.base import Base
from sqlalchemy.orm import relationship
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from uuid import uuid4


STUDY_STATUS_ENUM = ("planned", "locked", "completed", "in_progress")


class StudyItem(Base):
    __tablename__ = "study_items"
    __table_args__ = (
        CheckConstraint("units > 0", name="ck_study_items_units_positive"),
        {"schema": "stud_hub_schema"},  # <-- add schema here
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    term_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stud_hub_schema.terms.id", ondelete="CASCADE"),  # schema-qualified FK
        nullable=False,
        index=True,
    )
    requirement_category_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "stud_hub_schema.requirement_categories.id", ondelete="SET NULL"
        ),
        nullable=True,
        index=True,
    )

    course_code = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    units = Column(Integer, nullable=False, default=3)
    status = Column(
    Enum(
        *STUDY_STATUS_ENUM,
        name="study_status_enum",
        schema="stud_hub_schema",   # tell SQLAlchemy which schema
        create_type=False,          # do NOT try to CREATE TYPE
    ),
    nullable=False,
    default="planned",
)
    position_index = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    term = relationship("Term", back_populates="study_items")
    requirement_category = relationship(
        "RequirementCategory", back_populates="study_items"
    )
