# models.py
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
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("now()"))

    # relationships
    questions: Mapped[List["Question"]] = relationship(back_populates="user", cascade="all,delete-orphan")
    quizzes: Mapped[List["Quiz"]] = relationship(back_populates="user", cascade="all,delete-orphan")
#    responses: Mapped[List["Response"]] = relationship(back_populates="user", cascade="all,delete-orphan")
    flashcards: Mapped[List["Flashcard"]] = relationship(back_populates="user", cascade="all, delete-orphan")



# ---------------- Quizzes ----------------
class Quiz(Base):
    __tablename__ = "quizzes"
    __table_args__ = {"schema": "stud_hub_schema"}

    quiz_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("stud_hub_schema.users.user_id", ondelete="SET NULL"))
    questions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    time_taken: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # relationships
    user: Mapped[Optional[User]] = relationship(back_populates="quizzes")
    #responses: Mapped[List["Response"]] = relationship(back_populates="quiz", cascade="all,delete-orphan")


# ---------------- Questions ----------------
class Question(Base):
    __tablename__ = "questions"
    __table_args__ = {"schema": "stud_hub_schema"}

    question_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("stud_hub_schema.users.user_id", ondelete="SET NULL"))
    input_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    raw_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject_tag: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("now()"))

    # relationships
    user: Mapped[Optional[User]] = relationship(back_populates="questions")
    #responses: Mapped[List["Response"]] = relationship(back_populates="question", cascade="all,delete-orphan")

# ---------------- Flashcards ----------------
class Flashcard(Base):
    __tablename__ = "flashcards"
    __table_args__ = {"schema": "stud_hub_schema"}

    card_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("stud_hub_schema.users.user_id", ondelete="SET NULL"))
    cards: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # stores list of FlashcardItem dicts

    # relationships
    user: Mapped[Optional[User]] = relationship(back_populates="flashcards")