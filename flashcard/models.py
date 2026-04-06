from datetime import datetime
from typing import Optional, List

# REMOVED: from altair import Column  ← this was the root cause
from sqlalchemy import String, Integer, Text, TIMESTAMP, ForeignKey, text, Boolean, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from uuid import uuid4


class Base(DeclarativeBase):
    pass


class Quiz(Base):
    __tablename__ = "quizzes"
    __table_args__ = {"schema": "stud_hub_schema"}

    quiz_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        server_default=text("gen_random_uuid()"),
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject_tag: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    difficulty_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    estimated_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # ← "true" → True
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("now()"))

    questions: Mapped[List["QuizQuestion"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan"
    )
    analytics: Mapped[List["FlashcardAnalytics"]] = relationship(
        back_populates="deck", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("quiz_id", str(uuid4()))
        kwargs.setdefault("is_active", True)
        super().__init__(**kwargs)


class QuizQuestion(Base):
    __tablename__ = "questions"
    __table_args__ = {"schema": "stud_hub_schema"}

    question_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        server_default=text("gen_random_uuid()"),
    )
    quiz_id: Mapped[str] = mapped_column(
        ForeignKey("stud_hub_schema.quizzes.quiz_id", ondelete="CASCADE"),
        nullable=False,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(500), nullable=False)
    incorrect_answers: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=None)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=text("now()"))

    quiz: Mapped["Quiz"] = relationship(back_populates="questions")

    def __init__(self, **kwargs):
        kwargs.setdefault("question_id", str(uuid4()))
        super().__init__(**kwargs)


class FlashcardAnalytics(Base):
    __tablename__ = "flashcard_analytics"
    __table_args__ = {"schema": "stud_hub_schema"}

    analytics_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        server_default=text("gen_random_uuid()"),
    )
    deck_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("stud_hub_schema.quizzes.quiz_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)      # ← fixed
    card_reviewed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # ← fixed
    time_taken: Mapped[float] = mapped_column(Float, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=text("now()")
    )

    deck: Mapped["Quiz"] = relationship(back_populates="analytics")

    def __init__(self, **kwargs):
        kwargs.setdefault("analytics_id", str(uuid4()))
        kwargs.setdefault("card_reviewed", True)
        super().__init__(**kwargs)