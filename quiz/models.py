# models.py
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Integer, Float, Text, TIMESTAMP, ForeignKey, text, Boolean, ARRAY
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
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("now()"))

    # relationships
    questions: Mapped[List["Question"]] = relationship(back_populates="user", cascade="all,delete-orphan")
    quiz_attempts: Mapped[List["QuizAttempt"]] = relationship(back_populates="user", cascade="all,delete-orphan")


# ---------------- Quizzes (Global/Shared) ----------------
class Quiz(Base):
    __tablename__ = "quizzes"
    __table_args__ = {"schema": "stud_hub_schema"}

    quiz_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    difficulty_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    estimated_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # in minutes
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=True)
    quiz_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)  # admin user_id
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("now()"))

    # relationships
    questions: Mapped[List["QuizQuestion"]] = relationship(back_populates="quiz", cascade="all,delete-orphan")
    quiz_attempts: Mapped[List["QuizAttempt"]] = relationship(back_populates="quiz", cascade="all,delete-orphan")


# ---------------- Quiz Questions ----------------
class QuizQuestion(Base):
    __tablename__ = "questions"
    __table_args__ = {"schema": "stud_hub_schema"}

    question_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    quiz_id: Mapped[str] = mapped_column(ForeignKey("stud_hub_schema.quizzes.quiz_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("stud_hub_schema.users.user_id", ondelete="SET NULL"), nullable=True)
    input_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    raw_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject_tag: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    question_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    correct_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    incorrect_answers: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("now()"))

    # relationships
    quiz: Mapped["Quiz"] = relationship(back_populates="questions")
    user: Mapped[Optional["User"]] = relationship(back_populates="questions")


# ---------------- Quiz Attempts (User Results) ----------------
class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = {"schema": "stud_hub_schema"}

    attempt_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("stud_hub_schema.users.user_id", ondelete="CASCADE"), nullable=False)
    quiz_id: Mapped[str] = mapped_column(ForeignKey("stud_hub_schema.quizzes.quiz_id", ondelete="CASCADE"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    score_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    time_taken: Mapped[int] = mapped_column(Integer, nullable=False)  # in seconds
    answers: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Store detailed answers
    completed_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("now()"))

    # relationships
    user: Mapped["User"] = relationship(back_populates="quiz_attempts")
    quiz: Mapped["Quiz"] = relationship(back_populates="quiz_attempts")



