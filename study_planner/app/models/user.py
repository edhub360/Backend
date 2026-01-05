from app.db.base import Base
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "stud_hub_schema"}

    user_id = Column(UUID(as_uuid=True), primary_key=True)
