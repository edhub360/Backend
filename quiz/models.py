from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Float, Text, TIMESTAMP, ForeignKey, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from uuid import uuid4

class Base(DeclarativeBase):
    pass

# ---------------- Users ----------------
class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "stud_hub_schema"}
    
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    subscription_tier: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    study_goals: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    device_info: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    
    # Relationships
    quizzes: Mapped[List["Quiz"]] = relationship("Quiz", back_populates="user")

# ---------------- Quizzes ----------------
class Quiz(Base):
    __tablename__ = "quizzes"
    __table_args__ = {"schema": "stud_hub_schema"}
    
    quiz_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("stud_hub_schema.users.user_id"))
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    subject_tag: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    estimated_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    quiz_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="quizzes")
    questions: Mapped[List["Question"]] = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")

# ---------------- Questions ----------------
class Question(Base):
    __tablename__ = "questions"
    __table_args__ = {"schema": "stud_hub_schema"}
    
    question_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    quiz_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("stud_hub_schema.quizzes.quiz_id", ondelete="CASCADE"))
    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("stud_hub_schema.users.user_id"), nullable=True)
    input_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    raw_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject_tag: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    incorrect_answers: Mapped[list] = mapped_column(JSONB, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    
    # Relationships
    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="questions")
