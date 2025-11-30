# models.py
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Text, TIMESTAMP, ForeignKey, text, Boolean, ARRAY, Column, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from uuid import uuid4

class Base(DeclarativeBase):
    pass


# ---------------- Quizzes (Used as Flashcard Decks) ----------------
class Quiz(Base):
    __tablename__ = "quizzes"
    __table_args__ = {"schema": "stud_hub_schema"}

    quiz_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    difficulty_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    estimated_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("now()"))

    # relationships
    questions: Mapped[List["QuizQuestion"]] = relationship(back_populates="quiz", cascade="all,delete-orphan")


# ---------------- Quiz Questions (Used as Flashcard Items) ----------------
class QuizQuestion(Base):
    __tablename__ = "questions"
    __table_args__ = {"schema": "stud_hub_schema"}

    question_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    quiz_id: Mapped[str] = mapped_column(ForeignKey("stud_hub_schema.quizzes.quiz_id", ondelete="CASCADE"), nullable=False)
    
    # Flashcard mapping:
    # - question_text → Front of card (Question/Term)
    # - correct_answer → Back of card (Answer/Definition)  
    # - explanation → Hint (optional)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(500), nullable=False)
    incorrect_answers: Mapped[list] = mapped_column(ARRAY(Text), nullable=False)  # Not used in flashcards
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("now()"))

    # relationships
    quiz: Mapped["Quiz"] = relationship(back_populates="questions")

class FlashcardAnalytics(Base):
    __tablename__ = "flashcard_analytics"
    __table_args__ = {"schema": "stud_hub_schema"}

    analytics_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    deck_id: Mapped[str] = mapped_column(String, ForeignKey("stud_hub_schema.quizzes.quiz_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    card_reviewed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    time_taken: Mapped[float] = mapped_column(Float, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("now()"))