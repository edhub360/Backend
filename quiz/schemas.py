from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID


# ---------- Users ----------
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    language: Optional[str] = None
    subscription_tier: Optional[str] = None
    study_goals: Optional[Dict[str, Any]] = None
    device_info: Optional[Dict[str, Any]] = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    language: Optional[str] = None
    subscription_tier: Optional[str] = None
    study_goals: Optional[Dict[str, Any]] = None
    device_info: Optional[Dict[str, Any]] = None


class UserOut(UserBase):
    user_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ---------- Questions ----------
class QuestionBase(BaseModel):
    user_id: Optional[str] = None
    input_type: Optional[str] = None
    raw_input: Optional[str] = None
    subject_tag: Optional[str] = None
    difficulty: Optional[str] = None
    question_text: str
    correct_answer: str
    incorrect_answers: List[str]
    explanation: Optional[str] = None


class QuestionCreate(QuestionBase):
    quiz_id: str


class QuestionOut(QuestionBase):
    question_id: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


# ---------- Quiz Questions (for individual quiz questions) ----------
class QuizQuestionResponse(BaseModel):
    """Individual question within a quiz"""
    question_id: str
    question_text: str
    correct_answer: str
    incorrect_answers: List[str]
    explanation: Optional[str] = None
    difficulty: Optional[str] = None


# ---------- Quizzes (Global/Shared) ----------
class QuizListItem(BaseModel):
    """Quiz summary for listing all quizzes"""
    quiz_id: str
    title: str
    description: Optional[str] = None
    subject_tag: Optional[str] = None
    difficulty_level: Optional[str] = None
    estimated_time: Optional[int] = None  # in minutes
    total_questions: int = 0
    is_active: bool = True
    
    class Config:
        from_attributes = True


class QuizDetail(BaseModel):
    """Full quiz with all questions"""
    quiz_id: str
    title: str
    description: Optional[str] = None
    subject_tag: Optional[str] = None
    difficulty_level: Optional[str] = None
    estimated_time: Optional[int] = None
    questions: List[QuizQuestionResponse]
    
    class Config:
        from_attributes = True


class QuizCreate(BaseModel):
    """For creating new quizzes (admin only)"""
    title: str
    description: Optional[str] = None
    subject_tag: Optional[str] = None
    difficulty_level: Optional[str] = None
    estimated_time: Optional[int] = None
    tags: Optional[List[str]] = None
    is_active: bool = True


# ---------- Quiz Attempts (User Results) ----------
class AnswerDetail(BaseModel):
    """Individual answer within a quiz attempt"""
    question_id: str
    user_answer: str
    is_correct: bool


class QuizAttemptCreate(BaseModel):
    """Submit a quiz attempt"""
    user_id: str
    quiz_id: str
    score: int
    total_questions: int
    score_percentage: float
    time_taken: int  # in seconds
    answers: Optional[List[AnswerDetail]] = None


class QuizAttemptResponse(BaseModel):
    """Response after submitting a quiz attempt"""
    attempt_id: str
    user_id: str
    quiz_id: str
    score: int
    total_questions: int
    score_percentage: float
    time_taken: int
    completed_at: datetime
    
    class Config:
        from_attributes = True


class UserQuizHistory(BaseModel):
    """User's quiz attempt history"""
    attempt_id: str
    quiz_id: str
    quiz_title: str
    subject_tag: Optional[str] = None
    difficulty_level: Optional[str] = None
    score: int
    total_questions: int
    score_percentage: float
    time_taken: int
    completed_at: datetime
    
    class Config:
        from_attributes = True


class QuizStatistics(BaseModel):
    """Aggregated quiz performance statistics"""
    quiz_id: str
    title: str
    total_users_attempted: int = 0
    total_attempts: int = 0
    average_score: Optional[float] = None
    highest_score: Optional[float] = None
    lowest_score: Optional[float] = None
    average_time: Optional[float] = None
    
    class Config:
        from_attributes = True


# ---------- Legacy Support (Deprecated - for backward compatibility) ----------
class QuizQuestionItem(BaseModel):
    """Legacy format - kept for backward compatibility"""
    question: str
    options: List[str]
    correct: int
    explanation: Optional[str] = None


class QuizBase(BaseModel):
    """Legacy format - deprecated, use QuizDetail instead"""
    user_id: Optional[str] = None
    questions: Optional[List[QuizQuestionItem]] = None
    score: Optional[float] = None
    time_taken: Optional[int] = None


class QuizOut(QuizBase):
    """Legacy format - deprecated"""
    quiz_id: str
    
    class Config:
        from_attributes = True
